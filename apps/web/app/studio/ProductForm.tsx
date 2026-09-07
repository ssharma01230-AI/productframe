'use client';

import Image from 'next/image';
import { unstable_rethrow } from 'next/navigation';
import { useActionState, useEffect, useRef, useState } from 'react';
import { createProductAnalysisJob } from './actions';
import { UPLOAD_IMAGE_TYPES, validateUploadImages } from './upload-constraints';
import './product-upload.css';

type Selection = { id: string; file: File; preview: string };

export default function ProductForm({ open, onClose, message }: { open: boolean; onClose: () => void; message?: string }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const pickerRef = useRef<HTMLInputElement>(null);
  const galleryRef = useRef<HTMLDivElement>(null);
  const selectedRef = useRef<Selection[]>([]);
  const submitLock = useRef(false);
  const [selected, setSelected] = useState<Selection[]>([]);
  const [error, setError] = useState('');
  const [, formAction, submitting] = useActionState(async (_previous: null, data: FormData) => {
    await continueToAnalysis(data);
    return null;
  }, null);
  const [canPrevious, setCanPrevious] = useState(false);
  const [canNext, setCanNext] = useState(false);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!open || !dialog) return;
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    if (!dialog.open) dialog.showModal();
    return () => {
      dialog.close();
      document.body.style.overflow = previousOverflow;
      if (opener?.isConnected) opener.focus({ preventScroll: true });
    };
  }, [open]);

  useEffect(() => () => selectedRef.current.forEach(item => URL.revokeObjectURL(item.preview)), []);

  useEffect(() => {
    const gallery = galleryRef.current;
    if (!gallery || !open) return;
    const updateArrows = () => {
      setCanPrevious(gallery.scrollLeft > 2);
      setCanNext(gallery.scrollLeft + gallery.clientWidth < gallery.scrollWidth - 2);
    };
    updateArrows();
    const observer = new ResizeObserver(updateArrows);
    observer.observe(gallery);
    gallery.addEventListener('scroll', updateArrows, { passive: true });
    return () => { observer.disconnect(); gallery.removeEventListener('scroll', updateArrows); };
  }, [open, selected.length]);

  function chooseFiles(files: File[]) {
    if (submitLock.current || !files.length) return;
    const existing = new Set(selectedRef.current.map(item => item.id));
    const additions = files.filter(file => {
      const id = fileId(file);
      if (existing.has(id)) return false;
      existing.add(id);
      return true;
    });
    const validation = validateUploadImages([...selectedRef.current.map(item => item.file), ...additions]);
    if (validation) { setError(validation); return; }
    const next = [...selectedRef.current, ...additions.map(file => ({ id: fileId(file), file, preview: URL.createObjectURL(file) }))];
    selectedRef.current = next;
    setSelected(next);
    setError('');
  }

  function removeFile(id: string) {
    if (submitLock.current) return;
    const removed = selectedRef.current.find(item => item.id === id);
    const next = selectedRef.current.filter(item => item.id !== id);
    selectedRef.current = next;
    setSelected(next);
    if (removed) URL.revokeObjectURL(removed.preview);
    setError('');
  }

  async function continueToAnalysis(formData: FormData) {
    if (submitLock.current) return;
    const files = selectedRef.current.map(item => item.file);
    const validation = validateUploadImages(files);
    if (validation) { setError(validation); return; }
    // The native picker only holds the last selection; submit the reviewed set instead.
    formData.delete('images');
    files.forEach(file => formData.append('images', file, file.name));
    submitLock.current = true;
    setError('');
    try {
      await createProductAnalysisJob(formData);
    } catch (cause) {
      unstable_rethrow(cause);
      setError('We couldn’t start the upload. Your images are still here—please try again.');
    } finally {
      submitLock.current = false;
    }
  }

  function moveGallery(direction: number) {
    const gallery = galleryRef.current;
    if (!gallery) return;
    gallery.scrollBy({ left: direction * gallery.clientWidth, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  }

  return (
    <dialog ref={dialogRef} className="su-dialog" aria-labelledby="su-title" aria-describedby="su-description"
      onCancel={event => { event.preventDefault(); if (!submitting) onClose(); }}
      onClick={event => {
        if (event.target !== event.currentTarget || submitting) return;
        const bounds = event.currentTarget.getBoundingClientRect();
        if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) onClose();
      }}>
      <form action={formAction} className="su-form" aria-busy={submitting}>
        <header className="su-heading">
          <div><p className="su-eyebrow">YOUR PRODUCT IMAGES</p><h2 id="su-title">Upload your images.</h2><p id="su-description">Add your photos. We’ll find the products and get their details ready for review.</p></div>
          <button type="button" className="su-close" aria-label="Close image upload" disabled={submitting} onClick={onClose}><UploadIcon name="close" /></button>
        </header>
        <div className={'su-selection' + (selected.length ? ' has-images' : '')} onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); chooseFiles(Array.from(event.dataTransfer.files)); }}>
          <div className="su-picker-row">
            {!selected.length && <span className="su-empty-icon"><UploadIcon name="image" /></span>}
            <div className="su-picker-copy"><strong>{selected.length ? selected.length + (selected.length === 1 ? ' image selected' : ' images selected') : 'Start with the images you have.'}</strong><span>JPG, PNG or WebP · Up to 50 images</span></div>
            <div className="su-file-picker">
              <input ref={pickerRef} id="su-files" type="file" name="images" aria-label="Choose files" accept={UPLOAD_IMAGE_TYPES.join(',')} multiple disabled={submitting} onChange={event => { chooseFiles(Array.from(event.target.files ?? [])); event.target.value = ''; }} />
              <button type="button" className="su-button su-choose" autoFocus disabled={submitting} onClick={() => pickerRef.current?.click()}><UploadIcon name="plus" />Choose files</button>
            </div>
            {!selected.length && <p className="su-drop-hint">or drop them here · Multiple angles welcome</p>}
          </div>
          {selected.length > 0 && <div className="su-carousel">
            <button type="button" className="su-arrow" aria-label="Previous images" disabled={!canPrevious} onClick={() => moveGallery(-1)}><UploadIcon name="previous" /></button>
            <div className="su-grid" ref={galleryRef} role="list" aria-label="Selected images">
              {selected.map(item => <article key={item.id} className="su-card" role="listitem">
                <div className="su-photo"><Image src={item.preview} alt={'Selected image: ' + item.file.name} fill sizes="(max-width: 600px) 60vw, 200px" unoptimized /></div>
                <div className="su-card-copy"><strong title={item.file.name}>{item.file.name}</strong><small>{item.file.type.replace('image/', '').toUpperCase()} · {formatSize(item.file.size)}</small></div>
                <button type="button" className="su-remove" aria-label={'Remove ' + item.file.name} disabled={submitting} onClick={() => removeFile(item.id)}><UploadIcon name="close" /></button>
              </article>)}
            </div>
            <button type="button" className="su-arrow" aria-label="Next images" disabled={!canNext} onClick={() => moveGallery(1)}><UploadIcon name="next" /></button>
          </div>}
        </div>
        {(error || message) && <p className="su-error" role="alert">{error || message}</p>}
        <footer className="su-footer">
          <p role="status">{submitting ? 'Uploading your images and starting the analysis…' : 'Continue to analyse your images. You’ll review the details next.'}</p>
          <button className="su-button su-primary" type="submit" disabled={!selected.length || submitting}>{submitting ? 'Uploading…' : 'Continue'}<UploadIcon name="arrow" /></button>
        </footer>
      </form>
    </dialog>
  );
}

function fileId(file: File) { return JSON.stringify([file.name, file.size, file.lastModified, file.type]); }
function formatSize(bytes: number) { return bytes < 1_000_000 ? Math.max(1, Math.round(bytes / 1000)) + ' KB' : (bytes / 1_000_000).toFixed(1) + ' MB'; }
function UploadIcon({ name }: { name: 'close' | 'image' | 'plus' | 'previous' | 'next' | 'arrow' }) {
  const paths = { close: <path d="m6 6 12 12M18 6 6 18" />, image: <><rect x="3" y="3" width="18" height="18" rx="3" /><circle cx="8" cy="8" r="1.5" /><path d="m3 17 5-5 4 4 4-6 5 7" /></>, plus: <path d="M12 5v14M5 12h14" />, previous: <path d="m14 6-6 6 6 6" />, next: <path d="m10 6 6 6-6 6" />, arrow: <path d="M5 12h14m-5-5 5 5-5 5" /> };
  return <svg className="su-icon" viewBox="0 0 24 24" aria-hidden="true">{paths[name]}</svg>;
}
