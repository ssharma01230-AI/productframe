# Tops family template inventory

Step 1 of the Tops template-mapping repair. This inventory records the stable frontend IDs, source assets, and the intended visual composition. It is intentionally separate from implementation: the semantic mapping must be reviewed before backend prompt definitions are changed.

**Source:** `~/Downloads/tops-global` and `apps/web/app/studio/output-recipes.ts`.

**Evidence values are candidates only.** `front_view` means the product's front or a front-supported detail is needed; `rear_view` means the rear cannot be reliably generated from a front reference. Final evidence policy will be defined with the explicit backend templates.

| # | Stable template ID | Source asset | Intended composition | Presentation | Evidence candidate |
|---:|---|---|---|---|---|
| **Shirts** ||||| 
| 01 | `ecommerce-tops-shirts-01` | `shirts-ecom-01-lifestyle-seated-armchair.png` | Seated styled/lifestyle model, face excluded | worn, lifestyle seated | front_view |
| 02 | `ecommerce-tops-shirts-02` | `shirts-ecom-02-styled-front-model.png` | Styled front model, face excluded | worn, front model | front_view |
| 03 | `ecommerce-tops-shirts-03` | `shirts-ecom-03-folded-product-cuff-visible.png` | Folded product with cuff visible | product-only, folded | front_view |
| 04 | `ecommerce-tops-shirts-04` | `shirts-ecom-04-flat-lay-full-product.png` | Complete flat-lay product | product-only, flat lay | front_view |
| 05 | `ecommerce-tops-shirts-05` | `shirts-ecom-05-front-model-studio.png` | Straight-on studio model, face excluded | worn, front model | front_view |
| 06 | `ecommerce-tops-shirts-06` | `shirts-ecom-06-lifestyle-seated-model.png` | Seated styled model, face excluded | worn, lifestyle seated | front_view |
| 07 | `ecommerce-tops-shirts-07` | `shirts-ecom-07-detail-barrel-cuff.png` | Barrel-cuff construction detail | product detail, cuff | front_view |
| 08 | `ecommerce-tops-shirts-08` | `shirts-ecom-08-detail-poplin-fabric-fold.png` | Fabric/detail shot with fold | product detail, fabric | front_view |
| 09 | `ecommerce-tops-shirts-09` | `shirts-ecom-09-invisible-mannequin-front.png` | Complete front on invisible mannequin | product-only, mannequin | front_view |
| 10 | `ecommerce-tops-shirts-10` | `shirts-ecom-10-detail-collar-button-placket.png` | Collar, buttons and placket detail | product detail, collar/placket | front_view |
| 11 | `ecommerce-tops-shirts-11` | `shirts-ecom-11-detail-cuff-adjustment.png` | Cuff-adjustment detail | product detail, cuff | front_view |
| 12 | `ecommerce-tops-shirts-12` | `shirts-ecom-12-side-three-quarter-model.png` | Side/three-quarter model, face excluded | worn, angled model | front_view |
| 13 | `ecommerce-tops-shirts-13` | `shirts-ecom-13-side-three-quarter-product.png` | Side/three-quarter product presentation | product-only, angled | front_view |
| 14 | `ecommerce-tops-shirts-14` | `shirts-ecom-14-rear-product.png` | Complete rear product view | product-only, rear | rear_view |
| 15 | `ecommerce-tops-shirts-15` | `shirts-ecom-15-rear-model.png` | Rear model view, face excluded | worn, rear model | rear_view |
| **T-shirts / Casual Tops** ||||| 
| 01 | `ecommerce-tops-t-shirts-casual-tops-01` | `t-shirts-casual-ecom-01-front-product-shaped.png` | Front product with natural three-dimensional shaping | product-only, front | front_view |
| 02 | `ecommerce-tops-t-shirts-casual-tops-02` | `t-shirts-casual-ecom-02-hem-fit-detail-model.png` | Hem and fit detail on model | worn detail, hem | front_view |
| 03 | `ecommerce-tops-t-shirts-casual-tops-03` | `t-shirts-casual-ecom-03-folded-product.png` | Folded product | product-only, folded | front_view |
| 04 | `ecommerce-tops-t-shirts-casual-tops-04` | `t-shirts-casual-ecom-04-front-model.png` | Front model with one hand in trouser pocket, face excluded | worn, front model | front_view |
| 05 | `ecommerce-tops-t-shirts-casual-tops-05` | `t-shirts-casual-ecom-05-front-invisible-mannequin.png` | Complete front on invisible mannequin | product-only, front mannequin | front_view |
| 06 | `ecommerce-tops-t-shirts-casual-tops-06` | `t-shirts-casual-ecom-06-rear-model.png` | Rear model, face excluded | worn, rear model | rear_view |
| 08 | `ecommerce-tops-t-shirts-casual-tops-08` | `t-shirts-casual-ecom-08-side-three-quarter-invisible-mannequin.png` | Side/three-quarter on invisible mannequin | product-only, angled mannequin | front_view |
| 09 | `ecommerce-tops-t-shirts-casual-tops-09` | `t-shirts-casual-ecom-09-fabric-knit-texture-detail.png` | Fabric/knit texture detail with slight twist | product detail, fabric | front_view |
| 10 | `ecommerce-tops-t-shirts-casual-tops-10` | `t-shirts-casual-ecom-10-rear-invisible-mannequin.png` | Complete rear on invisible mannequin | product-only, rear mannequin | rear_view |
| **Sleeveless Tops** ||||| 
| 01 | `ecommerce-tops-sleeveless-tops-01` | `sleeveless-ecom-01-rear-model.png` | Rear model, face excluded | worn, rear model | rear_view |
| 02 | `ecommerce-tops-sleeveless-tops-02` | `sleeveless-ecom-02-front-model.png` | Front model, face excluded | worn, front model | front_view |
| 03 | `ecommerce-tops-sleeveless-tops-03` | `sleeveless-ecom-03-three-quarter-product.png` | Three-quarter product | product-only, angled | front_view |
| 04 | `ecommerce-tops-sleeveless-tops-04` | `sleeveless-ecom-04-flat-lay-full-product.png` | Complete flat-lay product | product-only, flat lay | front_view |
| 05 | `ecommerce-tops-sleeveless-tops-05` | `sleeveless-ecom-05-three-quarter-headless-mannequin.png` | Three-quarter headless mannequin | product-only, mannequin | front_view |
| 06 | `ecommerce-tops-sleeveless-tops-06` | `sleeveless-ecom-06-front-product.png` | Complete front product | product-only, front | front_view |
| 07 | `ecommerce-tops-sleeveless-tops-07` | `sleeveless-ecom-07-styled-model-no-face.png` | Styled model, face excluded | worn, styled model | front_view |
| **Knitwear** ||||| 
| 01 | `ecommerce-tops-knitwear-01` | `knitwear-ecom-01-folded-product.png` | Folded product | product-only, folded | front_view |
| 02 | `ecommerce-tops-knitwear-02` | `knitwear-ecom-02-neckline-detail.png` | Neckline detail | product detail, neckline | front_view |
| 03 | `ecommerce-tops-knitwear-03` | `knitwear-ecom-03-front-model.png` | Front model, face excluded | worn, front model | front_view |
| 04 | `ecommerce-tops-knitwear-04` | `knitwear-ecom-04-front-product.png` | Complete front product | product-only, front | front_view |
| 05 | `ecommerce-tops-knitwear-05` | `knitwear-ecom-05-rear-three-quarter-model.png` | Rear three-quarter model, face excluded | worn, rear angled model | rear_view |
| 06 | `ecommerce-tops-knitwear-06` | `knitwear-ecom-06-knit-fabric-detail.png` | Knit/fabric detail | product detail, fabric | front_view |
| 07 | `ecommerce-tops-knitwear-07` | `knitwear-ecom-07-seated-styled-model.png` | Seated styled model, face excluded | worn, lifestyle seated | front_view |
| 08 | `ecommerce-tops-knitwear-08` | `knitwear-ecom-08-flat-lay-full-product.png` | Complete flat-lay product | product-only, flat lay | front_view |
| 09 | `ecommerce-tops-knitwear-09` | `knitwear-ecom-09-rear-invisible-mannequin.png` | Rear invisible mannequin | product-only, rear mannequin | rear_view |
| 10 | `ecommerce-tops-knitwear-10` | `knitwear-ecom-10-front-invisible-mannequin.png` | Front invisible mannequin | product-only, mannequin | front_view |
| 11 | `ecommerce-tops-knitwear-11` | `knitwear-ecom-11-styled-model.png` | Styled model, face excluded | worn, styled model | front_view |
| **Hoodies** ||||| 
| 01 | `ecommerce-tops-hoodies-01` | `hoodies-ecom-01-flat-product.png` | Flat product presentation | product-only, flat lay | front_view |
| 02 | `ecommerce-tops-hoodies-02` | `hoodies-ecom-02-front-invisible-mannequin.png` | Front invisible mannequin | product-only, mannequin | front_view |
| 03 | `ecommerce-tops-hoodies-03` | `hoodies-ecom-03-back-invisible-mannequin.png` | Back invisible mannequin | product-only, rear mannequin | rear_view |
| 04 | `ecommerce-tops-hoodies-04` | `hoodies-ecom-04-three-quarter-invisible-mannequin.png` | Three-quarter invisible mannequin | product-only, angled mannequin | front_view |
| 05 | `ecommerce-tops-hoodies-05` | `hoodies-ecom-05-front-model.png` | Front model, face excluded | worn, front model | front_view |
| 06 | `ecommerce-tops-hoodies-06` | `hoodies-ecom-06-back-model.png` | Rear model, face excluded | worn, rear model | rear_view |
| 07 | `ecommerce-tops-hoodies-07` | `hoodies-ecom-07-three-quarter-model.png` | Three-quarter model, face excluded | worn, angled model | front_view |
| 08 | `ecommerce-tops-hoodies-08` | `hoodies-ecom-08-back-model-adjusting-hood.png` | Rear model adjusting hood, face excluded | worn, rear model/action | rear_view |
| 09 | `ecommerce-tops-hoodies-09` | `hoodies-ecom-09-front-model-adjusting-hood.png` | Front model adjusting hood, face excluded | worn, front model/action | front_view |
| 10 | `ecommerce-tops-hoodies-10` | `hoodies-ecom-10-model-hands-in-trouser-pockets.png` | Front/standing model with hands in pockets, face excluded | worn, front model | front_view |
| 11 | `ecommerce-tops-hoodies-11` | `hoodies-ecom-11-seated-three-quarter-model.png` | Seated three-quarter model, face excluded | worn, angled seated model | front_view |
| 12 | `ecommerce-tops-hoodies-12` | `hoodies-ecom-12-full-length-model-face-excluded.png` | Full-length model, face excluded | worn, full body | front_view |

## Findings from the inventory

- There are 55 family-specific IDs: 15 shirts, 10 T-shirts/casual tops, 7 sleeveless tops, 11 knitwear and 12 hoodies.
- The family packs intentionally mix product-only, mannequin, model, rear, angled and detail compositions.
- The T-shirts/casual-tops family is explicitly benchmark-mapped in the frontend and backend. Its ten templates use version 2 prompts with distinct semantic profiles rather than sharing the generic `flat_product` profile.
- The frontend benchmark image, name, presentation type and evidence requirement are treated as the contract for each T-shirt template.
- Other families retain their existing family mappings and should be reviewed against their benchmark images before receiving the same versioned treatment.

## Review notes

The composition labels above are derived from the supplied filenames and the existing frontend asset list. Before implementation, visually spot-check any ambiguous asset (especially lifestyle, detail and angled images) and adjust the row rather than relying on the filename alone.
