# Output Details reviews — frontend category and family coverage

The source of eligibility is `apps/web/app/studio/output-recipes.ts`: dedicated Ecommerce recipe arrays, family mappings and `getOutputRecipes`. Reviewed remaining sets: 15 September 2026. These are documentation contracts, not evidence that backend generations have passed fidelity checks.

| Global category | Dedicated frontend family/set | Review document |
|---|---|---|
| Tops | Shirts | [Shirts](shirts-output-details-review.md) |
| Tops | T-shirts / casual tops | [T-shirts](tshirt-output-details-review.md) |
| Tops | Sleeveless tops | [Sleeveless](sleeveless-output-details-review.md) |
| Tops | Knitwear | [Knitwear](knitwear-output-details-review.md) |
| Tops | Hoodies | [Hoodies](hoodies-output-details-review.md) |
| Bottoms | Structured bottoms | [Structured bottoms](structured-bottoms-output-details-review.md) |
| Bottoms | Shorts | [Shorts](shorts-output-details-review.md) |
| Bottoms | Casual bottoms / joggers | [Joggers](joggers-output-details-review.md) |
| Bottoms | Leggings | [Leggings](leggings-output-details-review.md) |
| Bottoms | Skirts | [Skirts](skirts-output-details-review.md) |
| Outerwear | Category-wide shared set — 9 images | [Outerwear](outerwear-output-details-review.md) |
| Footwear | Category-wide shared set — 9 images | [Footwear](footwear-output-details-review.md) |
| Socks | Category-wide shared set — 8 images | [Socks](socks-output-details-review.md) |
| Underwear | `lower_body_underwear` only — 7 images | [Underwear](underwear-output-details-review.md) |

## Scope and exclusions

- Outerwear, Footwear and Socks have no separate subtype-specific image sets in the current selector. Separate documents for every coat, shoe or sock subtype would imply distinctions the frontend does not implement.
- Other underwear families have no dedicated Ecommerce templates in this mapping.
- The generic fallback `OUTPUT_RECIPES` includes shared stock-photo examples. These are not dedicated family benchmark sets; no extra family documents were inferred from them.
- Lifestyle and Campaign are output channels, not global product categories or product families. Their shared examples are outside these family Ecommerce reviews.
- Files on disk that are not referenced by the current mappings are excluded. Filename numbering does not always match display order.
- The ten existing Tops/Bottoms documents are linked, not re-audited or rewritten in this pass.

## Review cautions

The new four reviews cover 33 individually viewed images, with 16 Output Details fields per slot. Product identity and material instructions are source-dependent: a leather jacket, ribbed sock, trainer or boxer-brief benchmark does not require that construction in every upload. Tiny underwear assets cannot establish precise microtexture. Socks Heel Detail and Heel Detail on Foot use different crops; only the latter exposes skin above the cuff.
