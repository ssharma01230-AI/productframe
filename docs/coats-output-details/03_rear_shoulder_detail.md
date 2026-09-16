# Coats — Rear Shoulder Detail — No Face

- Global category: `outerwear`
- Eligible family: `coats` only
- Channel: `ecommerce`
- Document key: `03_rear_shoulder_detail` (documentation identifier, not a registered runtime template ID)
- Presentation mode: `model`
- Benchmark: [View image](references/03_rear_shoulder_detail.png)
- Status: Visually reviewed output specification; implementation is now wired across the frontend, backend, prompt compiler and worker.

## Benchmark observations

Supplied 03; centre-back seam visible to image right. Do not impose that seam on another coat.

The benchmark supplies composition, framing and presentation. The uploaded product supplies identity. Camel colour, double-breasted construction, button count, wool-like appearance and pockets are observations of this example, not mandatory features for all coats. Preserve the uploaded coat's actual length and proportions, material, colour, graphics, fastenings and construction.

## OUTPUT DETAILS

- Subject: Uploaded coat, using the `model` presentation defined above.
- Camera angle and orientation: Close rear three-quarter, near shoulder at image left.
- Framing and crop: Nape, collar, shoulder and upper back fill frame; exclude face, hands, cuffs and hem.
- Product position and pose: Shoulder curves across left foreground; back extends to right edge.
- Product scale: Local detail fills the frame at the benchmark scale.
- Silhouette: Preserve the uploaded coat's outline and fit within this crop; do not turn another coat into the benchmark's tailored double-breasted shape.
- Visible construction: Actual rear collar, shoulder seams and upper-back construction.
- Garment volume: Natural worn shoulder curvature and upper-sleeve drape.
- Background: Light warm beige seamless studio background, approximately #C8C1B6; no location scenery or unrelated props.
- Lighting: Soft diffused directional studio light with gentle shadows; preserve real material sheen and surface relief. No hard flash, dramatic colour gels or exaggerated sharpening.
- Colour treatment: Preserve source product colour and tonal variation. Do not copy the benchmark camel colour or introduce a beige cast into the coat.
- Surface fidelity: Preserve evidenced texture scale. Several benchmark fronts show pronounced swirling surface detail; do not transfer this to a plain coat or invent fibres, ornament, weave or embroidery.
- Secondary styling: Use a restrained light neutral underlayer and simple trousers; where shoes are in frame, use understated footwear consistent with the selected styling. Match framing and pose, not benchmark model identity. Hands stay outside pockets.
- Composition: One continuous portrait ecommerce photograph, approximately 4:5; one coat only. No collage, inset, duplicated view, added text, watermark or decorative accessories.

## Source evidence and uncertainty

- Recommended evidence tags: `rear_view`.
- Required visual coverage for faithful reproduction: Upper-back and relevant shoulder reference; front imagery alone cannot establish rear details.
- Evidence tags alone do not prove adequate coverage or resolution; inspect the referenced surface and crop.
- Never treat an unseen surface as plain or copy front decoration onto rear/side surfaces. Rear seams, vents, lining, labels and artwork need supporting product evidence; this benchmark is not that evidence for another product.
- If the existing Continue anyway workflow is used with missing evidence, retain its missing-reference disclaimer. The resulting unseen details remain inferred, not verified. These documents do not change the current workflow or implement new gates.

## Review checks

- Match the stated orientation, crop, pose and presentation mode.
- Preserve coat identity and construction from uploaded references, including decoration placement by surface.
- Confirm the face is excluded and hands/hem obey the stated crop.
- Check for fabricated texture, fastenings, labels, seams and rear details before approving the generated output.
