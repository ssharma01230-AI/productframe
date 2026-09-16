# Coats — Fabric and Edge Detail

- Global category: `outerwear`
- Eligible family: `coats` only
- Channel: `ecommerce`
- Document key: `05_fabric_detail` (documentation identifier, not a registered runtime template ID)
- Presentation mode: `garment`
- Benchmark: [View image](references/05_fabric_detail.png)
- Status: Visually reviewed output specification; implementation is now wired across the frontend, backend, prompt compiler and worker.

## Benchmark observations

Supplied 05; an angular folded edge over cloth, not a featureless fabric swatch. Exact named garment part cannot be established from this crop.

The benchmark supplies composition, framing and presentation. The uploaded product supplies identity. Camel colour, double-breasted construction, button count, wool-like appearance and pockets are observations of this example, not mandatory features for all coats. Preserve the uploaded coat's actual length and proportions, material, colour, graphics, fastenings and construction.

## OUTPUT DETAILS

- Subject: Uploaded coat, using the `garment` presentation defined above.
- Camera angle and orientation: Very close oblique macro of a supported fabric edge.
- Framing and crop: Fabric fills every edge of frame; no whole garment, model or backdrop visible.
- Product position and pose: Folded edge corner occupies upper-left/centre, with another diagonal edge at right.
- Product scale: Local detail fills the frame at the benchmark scale.
- Silhouette: Preserve the uploaded coat's outline and fit within this crop; do not turn another coat into the benchmark's tailored double-breasted shape.
- Visible construction: Existing edge finish, stitching and surface texture only where supported by source detail.
- Garment volume: Local fabric thickness, edge relief and soft contact shadow; no inflated volume.
- Background: No exposed background; the material fills the frame.
- Lighting: Soft diffused directional studio light with gentle shadows; preserve real material sheen and surface relief. No hard flash, dramatic colour gels or exaggerated sharpening.
- Colour treatment: Preserve source product colour and tonal variation. Do not copy the benchmark camel colour or introduce a beige cast into the coat.
- Surface fidelity: Preserve evidenced texture scale. Several benchmark fronts show pronounced swirling surface detail; do not transfer this to a plain coat or invent fibres, ornament, weave or embroidery.
- Secondary styling: No person, skin, underlayer, trousers, footwear, hanger or visible support.
- Composition: One continuous portrait ecommerce photograph, approximately 4:5; one coat only. No collage, inset, duplicated view, added text, watermark or decorative accessories.

## Source evidence and uncertainty

- Recommended evidence tags: `detail`.
- Required visual coverage for faithful reproduction: Sharp close-up of the intended material/edge; a distant front photo does not prove fibre or stitch detail.
- Evidence tags alone do not prove adequate coverage or resolution; inspect the referenced surface and crop.
- Never treat an unseen surface as plain or copy front decoration onto rear/side surfaces. Rear seams, vents, lining, labels and artwork need supporting product evidence; this benchmark is not that evidence for another product.
- If the existing Continue anyway workflow is used with missing evidence, retain its missing-reference disclaimer. The resulting unseen details remain inferred, not verified. These documents do not change the current workflow or implement new gates.

## Review checks

- Match the stated orientation, crop, pose and presentation mode.
- Preserve coat identity and construction from uploaded references, including decoration placement by surface.
- Confirm macro detail is supported by adequate-resolution source imagery.
- Check for fabricated texture, fastenings, labels, seams and rear details before approving the generated output.
