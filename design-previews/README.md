# ProductFrame run review — static mock previews

Open `run-review-preview.html` directly in a browser. No build, package install,
Next.js server, API, database, sign-in, or AI key is required.

Each HTML file includes its own styles and script, so it can be copied and opened
independently. `run-review.css` and `run-review.js` are the readable source copies;
changes to them must also be copied into the HTML files. The previews reuse the
public Unsplash photos and Google Fonts already referenced by the
original `index.html`; photos/fonts require an internet connection, with a
clear unavailable-image fallback and system-font fallbacks when offline.

## Starting states

- `run-review-preview.html` — main preview, opening on the completed review.
- `run-review-loading.html` — "Reviewing your products", with three large blank
  thumbnails spanning the popup, a subtle shimmer and aligned batch progress.
  The three placeholders are decorative, not one thumbnail per uploaded image.
  The mock automatically completes after approximately 11 seconds.
- `run-review-complete.html` — four product cards, grouped thumbnails, editable
  product details, read-only category, approval/cancellation, and review progress.
- `run-review-cancel-confirmation.html` — completed review with the first
  product's small cancellation confirmation open.
- `run-review-rejected.html` — the rejected-image thumbnail and short reason.

## Mock interactions

- Select any product card; switch thumbnail crops; edit all suggested fields
  except category. Edits remain when switching between product cards.
- Discreet left/right arrows on the main image cycle through that product's
  images, wrapping at each end. Navigation also works after approval/cancellation.
- Approve the selected product. Approval requires a nonblank name. The separate
  Reject product button has been removed; the small X handles cancellation.
- Approved products show a small green check on their sidebar thumbnail. Undoing
  approval removes it; cancelled/pending products never show the approval badge.
  AI confidence labels are hidden from the product details.
- Use the small X within a product to open **Keep product / Cancel product**.
  Cancellation keeps the product in the run but excludes it from the library.
- **Change decision** lets you revisit a mock decision. Counts never double up.
- Cancelled products are excluded from the review denominator and counted
  separately: three approved and one cancelled shows 3 of 3 products reviewed,
  with 3 approved · 1 cancelled. Undoing cancellation restores the review total.
  Cancelling everything shows "All products cancelled", without a 0/0 bar.
- **Done reviewing** smoothly transitions to **Your edit is ready**: only the
  approved products, with their thumbnails and current edited names. Cancelled
  products are excluded. **Back to review** keeps all edits and decisions.
- **Produce outputs** opens a mock next step with Ecommerce, Lifestyle and
  Campaign options. Choose one or more, then **Preview generation** displays an
  explanatory message; it does not generate images or files. Output selections
  remain when navigating back and forth within the mock.
- If everything was cancelled, the summary says **No products approved** and
  offers **Back to review**, without an output action. Screen transitions move
  focus to the new heading and respect reduced-motion preferences.
- The header X closes the popup without discarding in-memory edits; reopen it
  from the background. Escape dismisses confirmation before closing the popup.
- The bottom preview-state controls reset mock edits and decisions; the replay
  icon only replays opening motion. Reloading also resets everything.
- Nothing is uploaded, saved, sent to an API, or written to browser storage.

## Fixed staging data

Run `RUN-2026-0001`: 15 uploaded images, 14 passed validation, 4 unique products,
1 rejected image. Product image groups contain 4 + 4 + 3 + 3 accepted images.
The grouped thumbnails reuse each reference photo at different crops: they are
illustrative mock views, not actual separate uploads or inferred back views.
The rejected-image reason is five words: “Not a wearable fashion product.”

The loading view always shows the same three placeholders regardless of upload
count. There is no filename list or separate text-heavy stage breakdown. Its percentage
tracks the overall analysis, while the checked-image count tracks validation.
Checking all images does not finish the run: grouping and preparation follow.
Only stage changes are announced; the animation respects reduced-motion settings.

Run processing and product decisions have separate counters. Cancelled products
remain visible and do not change the single rejected-upload count. The run-ID
metadata row and the redundant caption beneath each gallery have been removed.
AI-style descriptions are illustrative mock suggestions, not real analysis.

All preview code is contained in this directory. No production files were edited.
