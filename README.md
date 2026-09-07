# ProductFrame

ProductFrame is an AI-assisted fashion product content studio. It accepts product images, validates and analyses them, groups images into visible product identities, and presents the suggestions for human approval before publishing them to the Product Library.

The original prototype is preserved in [`index.html`](./index.html). It is a visual reference only. The production application is the Next.js/FastAPI implementation in `apps/web` and `services/`.

## Handover status

### Build status

The current application builds successfully as of the latest handover:

```text
pnpm typecheck:web   PASS
pnpm build:web      PASS
backend tests       261 PASS
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
- Bounded stage retries, with optional alternative-provider routing for transient failures; safety rejections are never retried through another provider.
- Backend-authoritative progress stage, message and counts. The review progress bar shows completed images divided by the current stage's image total, then completed products during detail preparation. Grouping displays an indeterminate bar while the batch comparison runs.
- Run review loading, product grouping, rejected-image views, editable metadata, approval, rejection, cancellation confirmation, and summary states.
- Read-only category field and required nonblank product names.
- Approve all saves the remaining unreviewed drafts in one transaction, including their edits, while preserving existing approvals, rejections and cancellations. Invalid drafts prevent the batch from saving, and retrying an approval does not create duplicate products.
- Approved products can still be cancelled from run review. Cancellation removes them from the Product Library and approved summary while preserving their details and source uploads in the run.
- Approved products in the Product Library.
- Workspace-scoped product deletion, including Product record, source assets, and MinIO cleanup.
- Product Library catalogue folders styled from the prototype, with one folder per real product, source-image collages, actual dates/counts, sorting, selection, and deletion confirmation.
- Product folders with refresh-safe URLs, associated uploads, full-image previews, private folder links, and upload ZIP downloads.
- A Gallery view reserved for approved generated outputs. Uploads remain inside product folders. Generated assets are persisted separately from source assets and can be stored in product folders and Gallery.
- A Create view inside Studio based on the prototype, with new-product upload and existing-catalogue paths. Its typography, stacked sections, card borders, and responsive layout have been browser-verified. `/studio?view=create` opens this view directly.
- Catalogue cards support selecting one or multiple products, then Choose outputs opens `/studio?view=create&step=outputs&product=<id>` (repeat `product` for multiple selections). Choices are resolved independently from each product's category. Outerwear uses ten leather-jacket Ecommerce reference images and matching titles/descriptions from `apps/web/public/output-examples/outerwear/`, with Over-the-Shoulder (No Face) replacing Front Far / Full Length in position 03 and the later sleeve-first image excluded. Footwear uses ten white-trainer Ecommerce reference images and matching titles/descriptions from `apps/web/public/output-examples/footwear/`. Socks uses the eight user-approved cream ribbed crew-sock Ecommerce previews from `apps/web/public/output-examples/socks/`, in attachment order. The selection includes four worn views, the original Heel Detail close-up, Flat Lay, Knit Texture and Folded Product; Side Profile, Cuff Detail and both Toe Detail versions are excluded. Exact approved attachments and checksums are recorded in `output/imagegen/socks-cream-crew/approved-selection.json`. The active order, replacements and archived originals are documented in [`output/imagegen/socks-cream-crew/README.md`](output/imagegen/socks-cream-crew/README.md). These three categories retain the prototype's 24 Lifestyle and Campaign choices, giving Socks 32 choices in total; all remaining product categories retain all 36 default choices. The socks revisions leave the Outerwear and Footwear sets unchanged. Reference previews are illustrative catalogue examples, not generated assets posted to a product's library. Review selection opens a centred popup with the same selected output thumbnails grouped by product; Back, Close, Escape and the backdrop dismiss it without losing choices. Product selections survive navigation in the URL; output choices remain in the current page session. Frontend output submission remains an integration task; backend generation jobs, previews, review and final asset persistence are implemented.
- The Outerwear, Footwear and Socks Ecommerce example images have the same conservative deterministic finishing profile applied in place: `1.055x` contrast, `1.075x` colour and an unsharp mask with radius `1.15`, strength `72%` and threshold `4`. All remain `1122x1402` PNGs. This is a presentation treatment for static template examples and does not make them generated product assets.

### Product categories and subtype routing

Recognition currently supports these clothing and fashion-product categories:

```text
tops, outerwear, bottoms, underwear, socks, footwear,
headwear, scarves, gloves, rings, neckwear, watches,
bracelets, earrings, belts
```

`accessories` is not a global category. Similar products are grouped economically: scarves include shawls and stoles, gloves include mittens, and rings, bracelets and earrings are routed separately. Bags, backpacks, luggage and purses are intentionally rejected as outside the supported clothing scope. Unknown subtypes should preserve their raw recognised product type and fall back to a category-compatible route rather than being forced into an incorrect subtype.

### Image generation, fidelity and finishing

The persisted image workflow is:

```text
load generation job
  -> build and persist the provider-neutral prompt
  -> generate image with the configured image model
  -> restore bounded source artwork when the template requires it
  -> validate that the visible result is the same sellable product
  -> apply conservative deterministic finishing
  -> store preview and pause for human review
  -> on approval, copy the reviewed preview to final storage
```

`services/api/src/productframe_api/generation_prompts.py` assembles product context, references, template instructions, negative constraints, source rotation and artwork policy. `services/api/src/productframe_api/generation_templates.py` defines category-compatible templates and whether source artwork should be fully, partially, conditionally or never visible.

`services/worker/src/productframe_worker/fidelity_validator.py` has three separate responsibilities that must remain ordered:

1. `restore()` attempts masked source-pixel restoration only for confident, bounded artwork regions. It fails closed when a usable mask or destination garment surface cannot be established.
2. `validate()` uses a vision model to reject a materially different sellable product. A rejected output is stored under a `rejected/` object key and is never exposed as the review preview.
3. `finish_generated_image()` performs presentation-only pixel processing after validation: `1.055x` contrast, `1.075x` colour and a small-radius unsharp mask (`1.15`, `72%`, threshold `4`). It preserves dimensions, supported image format, alpha and generation metadata. It does not crop, segment, inpaint, regenerate or move product details. Finishing is fail-open: if it cannot decode or save an unexpected provider format, the already validated image is stored unchanged.

The order is deliberate. Recognition, prompt construction, generation, restoration and the fidelity decision receive no sharpened or saturation-adjusted input. The human reviewer sees the finished preview, and the approved final is the same reviewed image.

The current image model is `gpt-image-2-2026-04-21`. Local tests showed strong reproduction for a printed navy T-shirt and an all-over patterned tunic. A difficult octopus graphic test exposed a limitation in the current colour-distance artwork mask: it correctly failed closed rather than publishing a contaminated rectangular source crop. Improve general artwork segmentation before treating that case as solved; do not add product-specific or octopus-specific schemas, prompts or scripts.

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
│   │   ├── OutputSelection.tsx    Category-adaptive template selection and review popup
│   │   ├── output-recipes.ts      Frontend template metadata and example-image mapping
│   │   ├── upload-constraints.ts Upload limits and accepted file constraints
│   │   ├── studio-home.css       Studio shell and overview styles
│   │   ├── product-upload.css    Upload dialog styles
│   │   └── run-review.css        Run review styles
│   ├── app/products/
│   │   ├── page.tsx              Server Product Library route
│   │   ├── ProductLibrary.tsx    Catalogue folders, Gallery, previews, selection, downloads, deletion
│   │   ├── LibraryShell.tsx      Shared Studio navigation and account layout
│   │   ├── library-types.ts      Product summary, upload, and generated-asset contracts
│   │   └── product-library.css   Scoped folder, gallery, detail, and dialog styles
│   ├── middleware.ts             Clerk route protection
│   ├── next.config.js            Next configuration and Server Action body limit
│   └── tests/                    Frontend test material, where present
├── services/api/
│   ├── src/productframe_api/main.py          FastAPI routes and persistence orchestration
│   ├── src/productframe_api/models.py        SQLAlchemy models and schemas
│   ├── src/productframe_api/image_recognition.py AI screening, analysis, categorisation, grouping
│   ├── src/productframe_api/category_registry.py Canonical supported categories and routing metadata
│   ├── src/productframe_api/category_schemas.py Category-specific structured recognition fields
│   ├── src/productframe_api/generation_templates.py Category/template generation registry
│   ├── src/productframe_api/generation_prompts.py Provider-neutral prompt and artwork policy assembly
│   ├── src/productframe_api/image_processing.py Image orientation and provider-safe normalisation
│   ├── src/productframe_api/analysis_router.py OpenAI/Gemini routing and persisted Gemini daily admissions
│   ├── src/productframe_api/analysis_limits.py Model-specific token sizing and shared request/token admission
│   ├── src/productframe_api/gemini_analysis.py Gemini structured-output transport and error handling
│   ├── src/productframe_api/analyze_cli.py   Local/manual recognition test entry point
│   ├── src/productframe_api/auth.py          Clerk token/JWKS authentication
│   ├── src/productframe_api/config.py        Environment configuration
│   ├── src/productframe_api/db.py            SQLAlchemy engine/session setup
│   └── migrations/versions/                  Alembic migrations through 0010, including generation persistence and graph identity
├── services/worker/
│   ├── src/productframe_worker/worker.py      Redis Streams worker and analysis/generation execution
│   ├── src/productframe_worker/generation_graph.py Durable LangGraph generation workflow
│   ├── src/productframe_worker/openai_image_provider.py OpenAI image-generation adapter
│   ├── src/productframe_worker/fidelity_validator.py Artwork restoration, fidelity gate, final finishing
│   ├── src/productframe_worker/checkpoint.py  PostgreSQL LangGraph checkpointer
│   ├── src/productframe_worker/generation_storage.py MinIO preview/final image storage
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

### Analysis providers and capacity

OpenAI analysis defaults to **GPT-4.1-mini**. Adding `GEMINI_API_KEY` enables hybrid routing with **Gemini 3.6 Flash**; set `ANALYSIS_PROVIDER_MODE=openai` to use OpenAI only. The router selects available capacity using request/token budgets, observed latency, and in-flight work. It prefers the image's previous provider when capacity is available, but can use another provider for the next stage or a transient failure. A retry repeats only the current stage, preserving completed earlier checks. Product-screening failures and provider safety blocks remain rejections.

The default concurrency is **3** across providers; the current local worker is configured with **6**. Each image still runs moderation → product screening → identity analysis → categorisation in order. Local file validation happens first. Grouping waits for all checks, always uses OpenAI, and sends the full set in one request when it fits the token budget; otherwise it uses bounded comparisons. Product details then run concurrently. Original image/product ordering is preserved, and progress/database writes stay on the coordinator thread.

The worker reads `services/worker/.env`; the standalone analyser reads the `.env` in its working directory. Image generation currently uses `OPENAI_IMAGE_MODEL=gpt-image-2-2026-04-21` when configured. Both service example files include these settings with blank credentials:

| Setting | Default | Purpose |
| --- | --- | --- |
| `OPENAI_MODEL` | `gpt-4.1-mini` | OpenAI vision model, including grouping. |
| `GEMINI_MODEL` | `gemini-3.6-flash` | Optional Gemini vision model. |
| `ANALYSIS_PROVIDER_MODE` | `hybrid` | Enables Gemini when its key is present; `openai` disables that route. |
| `ANALYSIS_CONCURRENCY` | `3` | Total parallel image or product-detail tasks, from 1 to 8. |
| `ANALYSIS_MAX_INPUT_TOKENS` | `110000` | Conservative OpenAI input cap per request. |
| `ANALYSIS_MAX_OUTPUT_TOKENS` | `4096` | Output space reserved per vision request on either provider. |
| `ANALYSIS_TOKENS_PER_MINUTE` | `180000` | OpenAI rolling token budget per model. |
| `ANALYSIS_REQUESTS_PER_MINUTE` | `60` | OpenAI rolling request budget per model. |
| `GEMINI_MAX_INPUT_TOKENS` | `32000` | Gemini input cap, also bounded by the global input cap. |
| `GEMINI_TOKENS_PER_MINUTE` | `225000` | Gemini rolling token budget. |
| `GEMINI_REQUESTS_PER_MINUTE` | `4` | Gemini rolling request budget. |
| `GEMINI_REQUESTS_PER_DAY` | `18` | Gemini daily request-attempt allowance. |
| `ANALYSIS_QUOTA_DB` | `<repository>/.cache/analysis-quotas.sqlite3` | Optional override for the persisted Gemini daily ledger. |
| `OPENAI_IMAGE_MODEL` | `gpt-image-2-2026-04-21` | OpenAI image-generation model used by the worker. |
| `GENERATION_MAX_ATTEMPTS` | `3` | Maximum bounded generation attempts. |

These are application budgets, not account allowances. Gemini's defaults leave headroom below the locally verified allowance of **5 requests/minute, 250000 tokens/minute, and 20 requests/day**; check the actual limits when using another account or model. Every retry reserves capacity again. Token/request admission and temporary cooldowns are shared across tasks on the same route; OpenAI moderation has its own request bucket. Estimates include model-specific image tokens, prompt/schema overhead, and output space. A request that cannot fit the configured capacity fails explicitly.

Gemini daily admissions persist across restarts, per credential fingerprint and model, using the **America/Los_Angeles calendar day**. The ledger counts individual request attempts, not images, and cannot see usage from other applications on the same provider project. When this allowance is exhausted, work continues on OpenAI when available.

Run **one worker process** for local development: analysis budgets and cooldowns are held in memory and are not distributed. Generation and analysis messages use Redis Streams consumer groups with acknowledgements. Pending-message reclamation, dead-letter handling and full multi-worker operational hardening remain outstanding.

Run the mocked API, pipeline, rate-limit, and worker regression checks without making paid model calls:

```bash
PYTHONPATH=services/worker/src services/api/.venv/bin/python -m pytest services/api/tests services/worker/tests -q
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
POST   /analysis-jobs/{job_id}/products/approve-all

GET    /products
GET    /products/{product_id}
GET    /products/{product_id}/download
POST   /products

POST   /generation-runs
GET    /generation-jobs/{job_id}
POST   /generation-jobs/{job_id}/review
DELETE /products/{product_id}
POST   /products/{product_id}/source-assets/upload-url
```

The frontend currently uses Server Actions for the initial upload path. Direct browser-to-MinIO uploads are intentionally deferred for a future performance pass.

Product Library reads preserve the existing product approval/visibility rules. Product summaries include category, creation date, upload count, and up to four real source-image previews. Folder detail returns all associated uploads; the download endpoint exports those uploads as a ZIP. Generated assets are persisted by the worker and surfaced through generation job and asset records; frontend gallery integration remains outstanding. Catalogue is the default `/products` view; `/products?product=<product_id>` opens a folder, and `/products?view=gallery` shows approved generated outputs only. Copying a folder link does not grant access outside its workspace.

## Current known issues and cautions

1. **Output selection does not yet submit generation work.** Existing catalogue products can be selected and category-adaptive templates can be chosen and reviewed, but Continue is not connected to generation-run creation, polling and approval UI.
2. **Analysis throughput remains capacity-limited.** OpenAI/Gemini routing overlaps independent image and product-detail tasks, while each image's gates retain their order. Token/request budgets, Gemini's daily allowance, retries, and large sets of distinct products can still make a run slow. Active-job crash/requeue recovery remains unfinished.
3. **Grouping is probabilistic.** It is safer to create an extra group than to merge visibly different products. More difficult fixture coverage is needed for colourways, patterns, footwear, lighting, folded/back/detail views, and near-identical garments.
4. **Run history is not yet a dedicated UI.** Jobs are durable in the database and a run can be reopened through a job ID, but there is no finished Run History screen/navigation.
5. **Subtype and category routing needs hardening.** Canonical subtype aliases and category-level fallbacks still need to be fully wired into recognition and template selection. Bags remain intentionally unsupported.
6. **Catalogue/output identity needs hardening.** Output selection must use durable run-scoped product IDs and should not depend on array position or transient client state.
7. **Frontend output generation is not connected.** The backend generation contract, queueing, storage, durable graph review state and review API are implemented. The frontend still needs to submit selected recipes, poll jobs, display previews and submit approval decisions.
8. **The current repository has uncommitted changes.** Preserve the work; inspect `git diff` and avoid broad cleanup until the new agent understands the implementation.
9. **Bounded artwork restoration is intentionally conservative.** The colour-distance mask works for isolated artwork on sufficiently distinct fabric, but rejects uncertain or contaminated crops. Keep the failure closed until a general segmentation approach is validated across varied products.

## Recommended next steps

Prioritize work in this order:

1. Start the web, API, worker, and infrastructure; verify `/studio` in a browser at desktop and mobile sizes. Test Create navigation, new upload, multi-product catalogue selection, category-adaptive Ecommerce templates, review selection, and return to Home.
2. Check browser console/network errors and correct any remaining rendering or image URL issues before adding features.
3. Add a dedicated durable Run History view and run detail route/list. It should show previous jobs, status, progress summary, rejected counts, and reopen run review by job ID.
4. Add automated recognition/grouping regression fixtures, especially distinguishable variants, same-product multi-view sets, similar garments, patterns, footwear, lighting changes, and rejected images.
5. Reduce AI latency by combining compatible analysis/categorisation calls, batching where reliable, caching, and preserving retry/backoff behaviour.
6. Improve persisted failure/retry messaging and progress granularity so the UI explains which stage failed and whether a retry is active.
7. Make catalogue and output selections use durable Product IDs and run-scoped identity consistently.
8. Connect Continue in output selection to the generation contract, including selected recipe submission, job polling, preview display and review actions.
9. Add generation fan-out for multiple products/templates in one run.
10. Replace Server Action uploads with direct browser-to-MinIO multipart uploads for large batches, while retaining validation and workspace authorization.
11. Once stable, remove accidental generated files from the change set, review secrets, create a clean commit, and update this handover.

## Validation commands

```bash
pnpm typecheck:web
pnpm build:web

# Product Library API: tenant isolation, approval visibility, source associations, ZIP exports
services/api/.venv/bin/python -m pytest services/api/tests/test_product_library.py -q

# API compilation check
cd services/api
.venv/bin/python -m compileall src

# Apply schema
.venv/bin/alembic upgrade head
```

For recognition work, use the existing CLI in `services/api/src/productframe_api/analyze_cli.py` against a local image directory, but do not commit test images, generated outputs, or API responses containing sensitive data.

## Secrets and environment

Never commit `.env`, `.env.local`, API keys, Clerk secrets, JWT private material, MinIO credentials, or generated signed URLs. Use the root and per-service `.env.example` files as templates. If a secret appears in tracked history, rotate it rather than merely deleting the file.
