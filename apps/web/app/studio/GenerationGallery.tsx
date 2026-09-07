'use client';

import { useAuth } from '@clerk/nextjs';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';
import type { GenerationDecisionRequest, GenerationJobResponse, GenerationProduct, GenerationRunDetail } from './generation-types';
import './generation-gallery.css';

type ProductGroup = { product: GenerationProduct; jobs: GenerationJobResponse[] };

function countLabel(count: number, singular: string, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`;
}

function titleCase(value: string) {
  return value ? value.charAt(0).toUpperCase() + value.slice(1).toLowerCase() : 'Product';
}

function responseError(payload: unknown, fallback: string) {
  return payload && typeof payload === 'object' && 'detail' in payload && typeof payload.detail === 'string' ? payload.detail : fallback;
}

function groupStatus(jobs: GenerationJobResponse[]) {
  const ready = jobs.filter(job => Boolean(job.preview_url || job.asset?.image_url)).length;
  const failed = jobs.filter(job => job.status === 'failed').length;
  const active = Math.max(0, jobs.length - ready - failed);
  const parts = [];
  if (ready) parts.push(`${ready} ready`);
  if (active) parts.push(`${active} in progress`);
  if (failed) parts.push(`${failed} needs attention`);
  return parts.join(' · ');
}

function GenerationCard({ job, busy, onDecision, onRetry, onDelete }: {
  job: GenerationJobResponse;
  busy: boolean;
  onDecision: (job: GenerationJobResponse, decision: 'approved' | 'rejected') => void;
  onRetry: (job: GenerationJobResponse) => void;
  onDelete: (job: GenerationJobResponse) => void;
}) {
  const imageUrl = job.asset?.image_url || job.preview_url;
  const decision = job.review_decision;
  const failed = job.status === 'failed';
  const phase = failed ? 'failed' : imageUrl ? 'ready' : 'in-progress';
  return <article className={`pf-generation-card is-${phase}${decision ? ` is-${decision}` : ''}`}>
    <div className="pf-generation-card-media">
      {imageUrl ? <Image src={imageUrl} alt={`${job.product.name} — ${job.template_name}`} fill sizes="(max-width: 520px) 100vw, (max-width: 900px) 50vw, 280px" unoptimized />
        : failed ? <div className="pf-generation-card-error"><span aria-hidden="true">!</span><strong>We couldn’t create this image</strong><p>{job.error_message || 'Something interrupted the generation.'}</p></div>
          : <div className="pf-generation-loading"><span className="pf-generation-orb" aria-hidden="true"/><strong>In progress</strong><span>Your image is currently being generated</span></div>}
      <span className="pf-generation-card-phase">{titleCase(job.template_channel)}</span>
      <button type="button" className="pf-generation-card-delete" onClick={() => onDelete(job)} disabled={busy || job.status === 'generating'} aria-label={`Delete ${job.template_name}`} title="Delete output"><span aria-hidden="true">×</span></button>
    </div>
    <div className="pf-generation-card-footer"><div><span>{titleCase(job.template_channel)}</span><h3>{job.template_name}</h3></div></div>
    {failed ? <div className="pf-generation-retry"><button type="button" disabled={busy} onClick={() => onRetry(job)}>{busy ? 'Retrying…' : 'Try again'}</button></div>
      : imageUrl && !decision ? <div className="pf-generation-review-actions">
        <button type="button" disabled={busy} onClick={() => onDecision(job, 'rejected')} aria-label={`Reject ${job.template_name}`}>Reject</button>
        <button className="approve" type="button" disabled={busy} onClick={() => onDecision(job, 'approved')} aria-label={`Approve ${job.template_name} and add it to Product Library`}>{busy ? 'Saving…' : 'Approve'}</button>
      </div>
        : null}
  </article>;
}

export default function GenerationGallery({ runId }: { runId: string }) {
  const router = useRouter();
  const { getToken } = useAuth();
  const [run, setRun] = useState<GenerationRunDetail | null>(null);
  const [error, setError] = useState('');
  const [busyJobId, setBusyJobId] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [notice, setNotice] = useState('');
  const [deleteCandidate, setDeleteCandidate] = useState<GenerationJobResponse | null>(null);

  useEffect(() => {
    let disposed = false;
    let timer: number | undefined;
    const controller = new AbortController();
    async function poll() {
      try {
        const token = await getToken();
        if (!token) throw new Error('Sign in again to view this generation.');
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/generation-runs/${encodeURIComponent(runId)}`, {
          headers: { Authorization: `Bearer ${token}` },
          cache: 'no-store',
          signal: controller.signal,
        });
        const payload = await response.json().catch(() => null) as GenerationRunDetail | { detail?: string } | null;
        if (!response.ok) throw new Error(responseError(payload, 'Generation progress could not be loaded.'));
        if (disposed) return;
        const snapshot = payload as GenerationRunDetail;
        setRun(snapshot);
        setError('');
        const needsLiveUpdates = snapshot.counts.in_progress > 0;
        const needsFreshImageUrls = snapshot.counts.reviewed < snapshot.counts.ready;
        if (needsLiveUpdates || needsFreshImageUrls) {
          const delay = needsLiveUpdates ? (document.visibilityState === 'hidden' ? 10000 : 2000) : 60000;
          timer = window.setTimeout(poll, delay);
        }
      } catch (cause) {
        if (disposed || (cause instanceof DOMException && cause.name === 'AbortError')) return;
        setError(cause instanceof Error ? cause.message : 'Generation progress could not be loaded.');
        timer = window.setTimeout(poll, 5000);
      }
    }
    void poll();
    return () => {
      disposed = true;
      controller.abort();
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [getToken, reloadKey, runId]);

  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(''), 4000);
    return () => window.clearTimeout(timer);
  }, [notice]);

  const groups = useMemo<ProductGroup[]>(() => {
    const byProduct = new Map<string, ProductGroup>();
    for (const job of run?.jobs ?? []) {
      const group = byProduct.get(job.product.id);
      if (group) group.jobs.push(job);
      else byProduct.set(job.product.id, { product: job.product, jobs: [job] });
    }
    return [...byProduct.values()];
  }, [run?.jobs]);

  async function decide(job: GenerationJobResponse, decision: 'approved' | 'rejected') {
    if (busyJobId || job.review_decision) return;
    setBusyJobId(job.id);
    setError('');
    try {
      const token = await getToken();
      if (!token) throw new Error('Sign in again to review this image.');
      const payload: GenerationDecisionRequest = { decision };
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/generation-jobs/${encodeURIComponent(job.id)}/decision`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const result = await response.json().catch(() => null);
      if (!response.ok) throw new Error(responseError(result, 'Your decision could not be saved.'));
      setNotice(decision === 'approved' ? `${job.template_name} was added to Product Library.` : `${job.template_name} was rejected and not added to Product Library.`);
      setReloadKey(current => current + 1);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Your decision could not be saved.');
    } finally {
      setBusyJobId(null);
    }
  }

  async function deleteJob(job: GenerationJobResponse) {
    if (busyJobId || job.status === 'generating') return;
    setBusyJobId(job.id);
    setError('');
    try {
      const token = await getToken();
      if (!token) throw new Error('Sign in again to delete this image.');
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/generation-jobs/${encodeURIComponent(job.id)}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } });
      const result = await response.json().catch(() => null);
      if (!response.ok) throw new Error(responseError(result, 'The image could not be deleted.'));
      setDeleteCandidate(null);
      setNotice(`${job.template_name} was deleted.`);
      setReloadKey(current => current + 1);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The image could not be deleted.');
    } finally { setBusyJobId(null); }
  }

  async function retry(job: GenerationJobResponse) {
    if (busyJobId || job.status !== 'failed') return;
    setBusyJobId(job.id);
    setError('');
    try {
      const token = await getToken();
      if (!token) throw new Error('Sign in again to retry this image.');
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/generation-jobs/${encodeURIComponent(job.id)}/retry`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const result = await response.json().catch(() => null);
      if (!response.ok) throw new Error(responseError(result, 'The image could not be retried.'));
      setNotice(`${job.template_name} is back in progress.`);
      setReloadKey(current => current + 1);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The image could not be retried.');
    } finally {
      setBusyJobId(null);
    }
  }

  const counts = run?.counts;
  const total = run?.total_jobs ?? 0;
  const percent = total ? Math.round(((counts?.ready ?? 0) / total) * 100) : 0;
  const canProceed = Boolean(counts && counts.in_progress === 0 && counts.failed === 0 && counts.ready === total && counts.reviewed === counts.ready);
  const reviewNote = !counts ? 'Loading your images'
    : counts.in_progress ? `${countLabel(counts.in_progress, 'image')} ${counts.in_progress === 1 ? 'is' : 'are'} still in progress`
      : counts.failed ? `${countLabel(counts.failed, 'image')} ${counts.failed === 1 ? 'needs' : 'need'} to be retried`
        : counts.reviewed < counts.ready ? `${countLabel(counts.ready - counts.reviewed, 'image')} ${counts.ready - counts.reviewed === 1 ? 'is' : 'are'} ready for your decision`
          : `${counts.approved} approved · ${counts.rejected} rejected`;

  return <section className="pf-generation-gallery" aria-labelledby="pf-generation-gallery-title" aria-busy={!run || Boolean(counts?.in_progress)}>
    <header className="pf-generation-heading">
      <p className="pf-generation-eyebrow">OUTPUT STUDIO · {counts?.in_progress ? 'IN PROGRESS' : 'REVIEW'}</p>
      <h1 id="pf-generation-gallery-title">Your images are taking shape.</h1>
      <p>Ready images stay visible while the rest remain in progress. Approve the images you want to keep in your Product Library.</p>
    </header>

    {error && <div className="pf-generation-alert" role="alert">{error}<button type="button" onClick={() => setReloadKey(current => current + 1)}>Try again</button></div>}

    <section className="pf-generation-summary" aria-label="Generation summary">
      <div className="pf-generation-summary-total">
        <div><span>Progress</span><strong>{counts?.ready ?? 0} of {total} ready</strong></div>
        <div className="pf-generation-summary-progress" role="progressbar" aria-label="Image generation progress" aria-valuemin={0} aria-valuemax={total || 1} aria-valuenow={counts?.ready ?? 0}><span style={{ width: `${percent}%` }}/></div>
        <div className="pf-generation-summary-meta"><span>{counts?.in_progress ? `${countLabel(counts.in_progress, 'image')} in progress` : counts?.failed ? `${countLabel(counts.failed, 'image')} needs attention` : 'All images generated'}</span><span>{percent}% complete</span></div>
      </div>
      <div className="pf-generation-summary-stat"><span>Across</span><strong>{counts?.products ?? 0}</strong><small>{counts?.products === 1 ? 'product' : 'products'}</small></div>
      <div className="pf-generation-summary-stat"><span>Generated</span><strong>{counts?.ready ?? 0}</strong><small>images ready</small></div>
      <div className="pf-generation-summary-stat"><span>Reviewed</span><strong>{counts?.reviewed ?? 0} of {counts?.ready ?? 0}</strong><small>{counts?.reviewed ? `${counts.approved} approved · ${counts.rejected} rejected` : 'Choose approve or reject'}</small></div>
    </section>

    <div className="pf-generation-toolbar">Your images organised by product</div>

    {!run && !error ? <div className="pf-generation-initial-loading" role="status"><span className="pf-generation-orb" aria-hidden="true"/><p>Loading your generation…</p></div> : groups.map((group, groupIndex) => <section className="pf-generation-product" key={group.product.id} aria-labelledby={`pf-generation-product-${group.product.id}`}>
      <header className="pf-generation-product-heading">
        <div className="pf-generation-product-identity">
          <span className="pf-generation-product-thumb">{group.product.image_url ? <Image src={group.product.image_url} alt="" fill sizes="49px" unoptimized/> : <span aria-hidden="true">P</span>}</span>
          <div><p>PRODUCT {String(groupIndex + 1).padStart(2, '0')} · {titleCase(group.product.category || 'product')}</p><h2 id={`pf-generation-product-${group.product.id}`}>{group.product.name}</h2><span>{countLabel(group.jobs.length, 'image')}</span></div>
        </div>
        <span className="pf-generation-product-status">{groupStatus(group.jobs)}</span>
      </header>
      <div className="pf-generation-grid">{group.jobs.map(job => <GenerationCard key={job.id} job={job} busy={busyJobId === job.id} onDecision={decide} onRetry={retry} onDelete={setDeleteCandidate}/>)}</div>
    </section>)}

    {deleteCandidate && <div className="pf-generation-delete-overlay" role="presentation" onClick={event => { if (event.target === event.currentTarget) setDeleteCandidate(null); }}><div className="pf-generation-delete-dialog" role="dialog" aria-modal="true" aria-labelledby="delete-generation-title"><h2 id="delete-generation-title">Delete this output?</h2><p>This will remove <strong>{deleteCandidate.template_name}</strong> from this run and Product Library if it was approved. This cannot be undone.</p><div className="pf-generation-delete-actions"><button type="button" onClick={() => setDeleteCandidate(null)} disabled={Boolean(busyJobId)}>Cancel</button><button type="button" className="danger" onClick={() => void deleteJob(deleteCandidate)} disabled={Boolean(busyJobId)}>{busyJobId === deleteCandidate.id ? 'Deleting…' : 'Delete output'}</button></div></div></div>}
    {notice && <div className="pf-generation-toast" role="status" aria-live="polite">{notice}</div>}
    <footer className="pf-generation-review-bar" aria-label="Image review progress">
      <div className="pf-generation-review-bar-inner">
        <div className="pf-generation-review-copy"><span>Review</span><strong>{counts?.reviewed ?? 0} of {total} {total === 1 ? 'image' : 'images'} reviewed</strong><small>{reviewNote}</small></div>
        <button type="button" className="pf-generation-library-button" disabled={!canProceed} onClick={() => router.push('/products?view=gallery')}>Proceed to Product Library <span aria-hidden="true">→</span></button>
      </div>
    </footer>
  </section>;
}
