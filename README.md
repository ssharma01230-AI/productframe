# ProductFrame

ProductFrame is an AI-assisted fashion product content studio. It accepts product images, validates and analyses them, groups images into visible product identities, and presents the suggestions for human approval before publishing them to the Product Library.

The original prototype is preserved in [`index.html`](./index.html). It is a visual reference only. The production application is the Next.js/FastAPI implementation in `apps/web` and `services/`.

## Handover status

### Build status

The current application builds successfully as of the latest handover:

```text
pnpm typecheck:web   PASS
pnpm build:web      PASS
```

The Next.js build completes for `/`, `/studio`, and `/products`. Build output contains existing Autoprefixer warnings about `start`/`end` flex values and a workspace-root warning caused by multiple lockfiles; these are non-fatal.

The repository currently contains a large amount of uncommitted implementation work. Do not assume `git status` represents only the latest change. Review the complete diff before committing or resetting anything.

### Implemented vertical slice

The following workflow is implemented end to end:

```text
Upload up to 50 images
  -> create durable analysis job
  -> validate/screen images
  -> analyse every accepted image
  -> categorise and group by visible product identity
  -> synthesise product suggestions
  -> persist progress and results
  -> review in the Studio run popup
  -> edit metadata
  -> approve, reject, or cancel each product
  -> publish approved products to Product Library
```

AI output is never final automatically. Approval is required before a product enters the catalogue.

Implemented behaviour includes:

- Clerk authentication and workspace-scoped tenancy.
- Clerk JWT/JWKS validation in the API.
- PostgreSQL persistence for workspaces, products, source assets, analysis jobs, decisions, and progress.
- Redis-backed durable worker execution.
- MinIO object storage with signed upload/read URLs.
- Image validation before downstream AI processing.
- Per-image analysis before grouping.
- Grouping based on general catalogue identity and visible evidence, rather than broad garment category alone.
- Separate groups for visibly distinguishable variants; uncertain groups should remain separate.
- Rejected images remain visible in the run and cannot be overridden.
- Three automatic retries for analysis failures.
- Backend-authoritative progress stage, message, completed count, total, and percentage.
- Run review loading, product grouping, rejected-image views, editable metadata, approval, rejection, cancellation confirmation, and summary states.
- Read-only category field and required nonblank product names.
- Approved products in the Product Library.
- Workspace-scoped product deletion, including Product record, source assets, and MinIO cleanup.
- Product Library deletion confirmation.
- A Create view inside Studio based on the prototype, with new-product upload and existing-catalogue paths. The Create view was recently CSS-scoped after a browser rendering conflict; it still needs browser verification at desktop and mobile widths.

A recent CLI fixture test used 15 images and produced:

```text
15 images
14 passed validation
1 rejected image
4 unique products
```

The test output was temporary and was deleted; it is not a persisted regression fixture.

## Repository map

```text
.
├── apps/web/                    Next.js frontend application
│   ├── app/page.tsx             Root/landing route
│   ├── app/layout.tsx           Clerk provider, fonts, global layout
│   ├── app/globals.css          Legacy/prototype-derived global styles and Product Library styles
│   ├── app/studio/
│   │   ├── page.tsx             Server route; loads workspace, products, and optional run results
│   │   ├── StudioHome.tsx        Client Studio shell, sidebar, overview, Create navigation
│   │   ├── CreateView.tsx        Create page for new or existing products
│   │   ├── ProductForm.tsx       Upload dialog/form
│   │   ├── actions.ts            Server Action upload flow and job creation
│   │   ├── RunReview.tsx         Client run-review popup and polling UI
│   │   ├── upload-constraints.ts Upload limits and accepted file constraints
│   │   ├── studio-home.css       Studio shell and overview styles
│   │   ├── product-upload.css    Upload dialog styles
│   │   └── run-review.css        Run review styles
│   ├── app/products/
│   │   ├── page.tsx              Server Product Library route
│   │   └── ProductLibrary.tsx    Client catalogue and deletion interactions
│   ├── middleware.ts             Clerk route protection
│   ├── next.config.js            Next configuration and Server Action body limit
│   └── tests/                    Frontend test material, where present
├── services/api/
│   ├── src/productframe_api/main.py          FastAPI routes and persistence orchestration
│   ├── src/productframe_api/models.py        SQLAlchemy models and schemas
│   ├── src/productframe_api/image_recognition.py AI screening, analysis, categorisation, grouping
│   ├── src/productframe_api/analyze_cli.py   Local/manual recognition test entry point
│   ├── src/productframe_api/auth.py          Clerk token/JWKS authentication
│   ├── src/productframe_api/config.py        Environment configuration
│   ├── src/productframe_api/db.py            SQLAlchemy engine/session setup
│   └── migrations/versions/                  Alembic migrations 0001 through 0007
├── services/worker/
│   ├── src/productframe_worker/worker.py      Redis worker and analysis pipeline execution
│   └── src/productframe_worker/cli.py         Worker command-line entry point
├── compose.yaml                  PostgreSQL, Redis, and MinIO local infrastructure
├── design-previews/               Static run-review design references; not production routes
├── index.html                     Original complete visual prototype/reference
├── package.json                   Root scripts and workspace commands
├── pnpm-workspace.yaml            pnpm workspace definition
└── .env.example files             Safe configuration templates; never put secrets here
```

### How to interpret the folders

- Change production UI in `apps/web/app`, not in `index.html` or `design-previews/`.
- Treat `index.html` as a design reference. It contains prototype CSS and interaction ideas for Create, catalogue, history, output, and settings views that have not all been ported.
- `design-previews/` contains isolated static experiments, especially the run-review states. Keep these independent from production components.
- Put API contracts, workspace authorization, database writes, and signed storage operations in `services/api`.
- Put long-running AI work in `services/worker`; the web request must not perform the full analysis synchronously.
- `services/api/image_recognition.py` owns recognition prompts and grouping logic. Changes here can alter catalogue identity behaviour and must be regression-tested.
- `services/api/migrations/` is the source of database schema history. Add a migration for schema changes; do not edit an already-applied migration casually.
- Local generated files such as `.next`, Python `__pycache__`, egg-info, `.env`, and `.env.local` are not application source and should not be committed.

## Local setup

Requirements: Node.js 20+, pnpm, Python 3.12+, Docker Desktop, Clerk credentials, and an OpenAI API key for real analysis.

```bash
cp .env.example .env
# create/update apps/web/.env.local and service env files from their examples
docker compose up -d
pnpm install
```

Run the web app:

```bash
pnpm dev:web
```

Run the API in a second terminal:

```bash
cd services/api
python -m venv .venv
.venv/bin/pip install -e .
.venv/bin/alembic upgrade head
.venv/bin/uvicorn productframe_api.main:app --reload --port 8000
```

Run the worker in a third terminal:

```bash
cd services/worker
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e ../api -e .
.venv/bin/productframe-worker run
```

Open:

- Web app: <http://localhost:3000>
- API health: <http://localhost:8000/health>
- API readiness: <http://localhost:8000/ready>
- Product Library: <http://localhost:3000/products>
- Studio: <http://localhost:3000/studio>
- Prototype: open [`index.html`](./index.html) directly

If Next development enters a corrupted hot-reload state, stop it, remove `apps/web/.next`, and restart. Do not remove source files.

## Important API routes

All application routes require the authenticated workspace context unless noted otherwise.

```text
GET    /health
GET    /ready
GET    /me
GET    /workspaces/current

POST   /analysis-jobs
GET    /analysis-jobs/{job_id}
GET    /analysis-jobs/{job_id}/results
PATCH  /analysis-jobs/{job_id}/products/{product_number}

GET    /products
POST   /products
DELETE /products/{product_id}
POST   /products/{product_id}/source-assets/upload-url
```

The frontend currently uses Server Actions for the initial upload path. Direct browser-to-MinIO uploads are intentionally deferred for a future performance pass.

## Current known issues and cautions

1. **Create-page browser verification is outstanding.** The page now uses scoped `pf-create-*` classes and plain `<img>` tags to avoid global CSS and remote `next/image` conflicts. Verify the Create navigation, upload dialog, catalogue cards, and mobile layout in a real browser.
2. **OpenAI latency is high.** The worker currently makes many sequential calls. Rate limits, retries, and large batches can make a run slow.
3. **Grouping is probabilistic.** It is safer to create an extra group than to merge visibly different products. More difficult fixture coverage is needed for colourways, patterns, footwear, lighting, folded/back/detail views, and near-identical garments.
4. **Run history is not yet a dedicated UI.** Jobs are durable in the database and a run can be reopened through a job ID, but there is no finished Run History screen/navigation.
5. **Catalogue/output identity needs hardening.** Output selection must use durable run-scoped product IDs and should not depend on array position or transient client state.
6. **Output generation is not connected.** “Produce outputs” is still a future integration and needs a defined generation contract, queueing model, storage model, and review state.
7. **The current repository has uncommitted changes.** Preserve the work; inspect `git diff` and avoid broad cleanup until the new agent understands the implementation.

## Recommended next steps

Prioritize work in this order:

1. Start the web, API, worker, and infrastructure; verify `/studio` in a browser at desktop and mobile sizes. Test Create navigation, new upload, existing catalogue cards, and return to Home.
2. Check browser console/network errors and correct any remaining rendering or image URL issues before adding features.
3. Add a dedicated durable Run History view and run detail route/list. It should show previous jobs, status, progress summary, rejected counts, and reopen run review by job ID.
4. Add automated recognition/grouping regression fixtures, especially distinguishable variants, same-product multi-view sets, similar garments, patterns, footwear, lighting changes, and rejected images.
5. Reduce AI latency by combining compatible analysis/categorisation calls, batching where reliable, caching, and preserving retry/backoff behaviour.
6. Improve persisted failure/retry messaging and progress granularity so the UI explains which stage failed and whether a retry is active.
7. Make catalogue and output selections use durable Product IDs and run-scoped identity consistently.
8. Define and implement the real output-generation contract, including worker jobs, generated asset persistence, storage URLs, and review/approval states.
9. Replace Server Action uploads with direct browser-to-MinIO multipart uploads for large batches, while retaining validation and workspace authorization.
10. Once stable, remove accidental generated files from the change set, review secrets, create a clean commit, and update this handover.

## Validation commands

```bash
pnpm typecheck:web
pnpm build:web

# API compilation check
cd services/api
.venv/bin/python -m compileall src

# Apply schema
.venv/bin/alembic upgrade head
```

For recognition work, use the existing CLI in `services/api/src/productframe_api/analyze_cli.py` against a local image directory, but do not commit test images, generated outputs, or API responses containing sensitive data.

## Secrets and environment

Never commit `.env`, `.env.local`, API keys, Clerk secrets, JWT private material, MinIO credentials, or generated signed URLs. Use the root and per-service `.env.example` files as templates. If a secret appears in tracked history, rotate it rather than merely deleting the file.
