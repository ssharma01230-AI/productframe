# Socks Ecommerce preview set

Eight approved Ecommerce previews for a fictional pair of unbranded cream ribbed crew socks, originally created with the built-in `image_gen` tool. The active images are exact copies of the eight attachments selected by the user, in attachment order. The archived [original pair product shot](01-pair-product-shot.png) established the reference pair; no real product photograph was supplied.

The [approved selection manifest](approved-selection.json) records each attachment, its saved copy and SHA-256 checksum. The `approved/` folder contains only this selection.

Original prompts and reference inputs: [prompts.json](prompts.json). Four replacement worn views: [worn-revisions.prompts.json](worn-revisions.prompts.json). Folded Product: [prompt](10-folded-product.prompt.json).

| App order | Output | Image |
| --- | --- | --- |
| 01 | Three-Quarter on Feet | [PNG](approved/01-three-quarter-on-feet.png) |
| 02 | Rear on Feet | [PNG](approved/03-rear-on-feet.png) |
| 03 | Folded Product | [PNG](approved/10-folded-product.png) |
| 04 | Flat Lay | [PNG](approved/04-flat-lay.png) |
| 05 | Heel Detail | [PNG](approved/06-heel-detail.png) |
| 06 | Knit Texture | [PNG](approved/08-knit-texture.png) |
| 07 | Front on Feet | [PNG](approved/09-front-on-feet.png) |
| 08 | Heel Detail on Foot | [PNG](approved/06-heel-detail-on-foot.png) |

The application numbers these eight choices consecutively. Source filenames retain their original numbers. Side Profile, Cuff Detail and both Toe Detail versions are excluded from this approved set.

The approved selection includes four worn views with an adult lower leg visible above the cuff, the original Heel Detail close-up, Flat Lay, Knit Texture and Folded Product. The latest explicit selection retains the original heel macro alongside Heel Detail on Foot. The construction, knit and newly revealed details are generated concepts, not verified specifications of an existing product.

Original and superseded previews remain archived at the top level of this folder. Only the eight approved files in the table are copied to `apps/web/public/output-examples/socks/` for the Ecommerce catalogue and selection-review thumbnails.

Socks retains the existing 24 Lifestyle and Campaign choices, giving 32 choices in total. Outerwear and Footwear keep their existing previews; all other product categories keep the default choices.

These images are illustrative output examples. They are not customer generations or Product Library entries, and selecting them does not submit a generation job.
