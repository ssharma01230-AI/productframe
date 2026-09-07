export const OUTPUT_CATEGORIES = ['Ecommerce', 'Lifestyle', 'Campaign'] as const;

export type OutputRecipe = {
  id: string;
  category: typeof OUTPUT_CATEGORIES[number];
  name: string;
  description: string;
  exampleImage: string;
};

// Reference images illustrate output types; they are never generated product assets.
export const OUTPUT_RECIPES: readonly OutputRecipe[] = [
  {
    "id": "ecommerce-clean-product-shot",
    "category": "Ecommerce",
    "name": "Clean Product Shot",
    "description": "The complete garment isolated against a neutral background for clear ecommerce presentation.",
    "exampleImage": "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=600&q=85"
  },
  {
    "id": "ecommerce-invisible-mannequin-shot",
    "category": "Ecommerce",
    "name": "Invisible Mannequin Shot",
    "description": "The garment appears naturally worn on an invisible mannequin, showing shape and volume without a visible person.",
    "exampleImage": "https://images.unsplash.com/photo-1525507119028-ed4c629a60a3?w=600&q=85"
  },
  {
    "id": "ecommerce-front-view",
    "category": "Ecommerce",
    "name": "Front View",
    "description": "A precise straight-on view showing the garment’s complete front silhouette and design details.",
    "exampleImage": "https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=600&q=85"
  },
  {
    "id": "ecommerce-back-view",
    "category": "Ecommerce",
    "name": "Back View",
    "description": "A precise rear view showing the garment’s back silhouette, construction and pattern placement.",
    "exampleImage": "https://images.unsplash.com/photo-1483985988355-763728e1935b?w=600&q=85"
  },
  {
    "id": "ecommerce-side-profile",
    "category": "Ecommerce",
    "name": "Side Profile",
    "description": "A side-on view showing the garment’s depth, length, shape and profile.",
    "exampleImage": "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=600&q=85"
  },
  {
    "id": "ecommerce-three-quarter-view",
    "category": "Ecommerce",
    "name": "Three-Quarter View",
    "description": "An angled view combining front and side perspectives to show the garment’s volume and silhouette.",
    "exampleImage": "https://images.unsplash.com/photo-1539109136881-3be0616acf4b?w=600&q=85"
  },
  {
    "id": "ecommerce-flat-lay",
    "category": "Ecommerce",
    "name": "Flat Lay",
    "description": "The garment arranged flat and photographed from above to show its complete shape and layout.",
    "exampleImage": "https://images.unsplash.com/photo-1496747611176-843222e1e57c?w=600&q=85"
  },
  {
    "id": "ecommerce-folded-product-shot",
    "category": "Ecommerce",
    "name": "Folded Product Shot",
    "description": "The garment neatly folded to show its colour, thickness, layering and fabric quality.",
    "exampleImage": "https://images.unsplash.com/photo-1547887538-e3a2f32cb1cc?w=600&q=85"
  },
  {
    "id": "ecommerce-fabric-detail",
    "category": "Ecommerce",
    "name": "Fabric Detail",
    "description": "A close-up image focused on the garment’s texture, weave, knit, finish and material character.",
    "exampleImage": "https://images.unsplash.com/photo-1551488831-00ddcb6c6bd3?w=600&q=85"
  },
  {
    "id": "ecommerce-construction-detail",
    "category": "Ecommerce",
    "name": "Construction Detail",
    "description": "A close-up showing functional details such as stitching, buttons, zips, seams, cuffs or collars.",
    "exampleImage": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=600&q=85"
  },
  {
    "id": "ecommerce-feature-close-up",
    "category": "Ecommerce",
    "name": "Feature Close-Up",
    "description": "A focused crop highlighting the garment’s most distinctive or commercially important feature.",
    "exampleImage": "https://images.unsplash.com/photo-1529139574466-a303027c1d8b?w=600&q=85"
  },
  {
    "id": "ecommerce-fabric-drape-shot",
    "category": "Ecommerce",
    "name": "Fabric Drape Shot",
    "description": "The garment gently folded, twisted or draped to show movement, flexibility and how the fabric falls.",
    "exampleImage": "https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?w=600&q=85"
  },
  {
    "id": "lifestyle-everyday-wear",
    "category": "Lifestyle",
    "name": "Everyday Wear",
    "description": "The garment worn naturally in a realistic everyday setting such as a street, café or home.",
    "exampleImage": "https://images.unsplash.com/photo-1529139574466-a303027c1d8b?w=600&q=85"
  },
  {
    "id": "lifestyle-full-outfit",
    "category": "Lifestyle",
    "name": "Full Outfit",
    "description": "The garment styled as part of a complete outfit, showing how it can be worn with complementary clothing.",
    "exampleImage": "https://images.unsplash.com/photo-1496747611176-843222e1e57c?w=600&q=85"
  },
  {
    "id": "lifestyle-detail-styling",
    "category": "Lifestyle",
    "name": "Detail Styling",
    "description": "A closer lifestyle view focused on how the garment’s texture, shape or design details appear when worn.",
    "exampleImage": "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=600&q=85"
  },
  {
    "id": "lifestyle-street-style",
    "category": "Lifestyle",
    "name": "Street Style",
    "description": "The garment worn in an urban environment with a natural, contemporary streetwear feel.",
    "exampleImage": "https://images.unsplash.com/photo-1483985988355-763728e1935b?w=600&q=85"
  },
  {
    "id": "lifestyle-studio-model-shot",
    "category": "Lifestyle",
    "name": "Studio Model Shot",
    "description": "The garment worn by a model in a clean studio setting with restrained styling and a simple background.",
    "exampleImage": "https://images.unsplash.com/photo-1539109136881-3be0616acf4b?w=600&q=85"
  },
  {
    "id": "lifestyle-natural-movement",
    "category": "Lifestyle",
    "name": "Natural Movement",
    "description": "The model captured walking, turning, reaching or moving naturally while wearing the garment.",
    "exampleImage": "https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=600&q=85"
  },
  {
    "id": "lifestyle-seated-portrait",
    "category": "Lifestyle",
    "name": "Seated Portrait",
    "description": "The model wearing the garment while seated, showing how it folds, drapes and behaves in a relaxed position.",
    "exampleImage": "https://images.unsplash.com/photo-1509631179647-0177331693ae?w=600&q=85"
  },
  {
    "id": "lifestyle-layering-shot",
    "category": "Lifestyle",
    "name": "Layering Shot",
    "description": "The garment styled underneath, over or alongside other clothing to demonstrate layering options.",
    "exampleImage": "https://images.unsplash.com/photo-1543076447-215ad9ba6923?w=600&q=85"
  },
  {
    "id": "lifestyle-seasonal-setting",
    "category": "Lifestyle",
    "name": "Seasonal Setting",
    "description": "The garment worn in an environment that reflects its intended season, such as a winter street or summer terrace.",
    "exampleImage": "https://images.unsplash.com/photo-1523381210434-271e8be1f52b?w=600&q=85"
  },
  {
    "id": "lifestyle-social-moment",
    "category": "Lifestyle",
    "name": "Social Moment",
    "description": "The garment worn during a natural social interaction, such as meeting friends, shopping or travelling.",
    "exampleImage": "https://images.unsplash.com/photo-1529139574466-a303027c1d8b?w=600&q=85"
  },
  {
    "id": "lifestyle-wardrobe-pairing",
    "category": "Lifestyle",
    "name": "Wardrobe Pairing",
    "description": "The garment shown alongside a specific complementary item, demonstrating a practical styling combination.",
    "exampleImage": "https://images.unsplash.com/photo-1496747611176-843222e1e57c?w=600&q=85"
  },
  {
    "id": "lifestyle-mirror-or-dressing-moment",
    "category": "Lifestyle",
    "name": "Mirror or Dressing Moment",
    "description": "A candid-style image showing the garment being considered, adjusted or worn in a dressing environment.",
    "exampleImage": "https://images.unsplash.com/photo-1483985988355-763728e1935b?w=600&q=85"
  },
  {
    "id": "campaign-campaign-hero",
    "category": "Campaign",
    "name": "Campaign Hero",
    "description": "The main branded campaign image designed to communicate the central idea, mood and visual identity.",
    "exampleImage": "https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=600&q=85"
  },
  {
    "id": "campaign-conceptual-product-portrait",
    "category": "Campaign",
    "name": "Conceptual Product Portrait",
    "description": "A stylised image placing the garment in a distinctive visual world that expresses the campaign concept.",
    "exampleImage": "https://images.unsplash.com/photo-1509631179647-0177331693ae?w=600&q=85"
  },
  {
    "id": "campaign-editorial-fashion-image",
    "category": "Campaign",
    "name": "Editorial Fashion Image",
    "description": "A high-end fashion image with considered styling, composition, lighting and art direction.",
    "exampleImage": "https://images.unsplash.com/photo-1539109136881-3be0616acf4b?w=600&q=85"
  },
  {
    "id": "campaign-brand-world-image",
    "category": "Campaign",
    "name": "Brand World Image",
    "description": "A campaign image that builds a recognisable visual environment around the clothing brand.",
    "exampleImage": "https://images.unsplash.com/photo-1529139574466-a303027c1d8b?w=600&q=85"
  },
  {
    "id": "campaign-graphic-product-composition",
    "category": "Campaign",
    "name": "Graphic Product Composition",
    "description": "A designed composition combining the garment with bold shapes, colour fields, patterns or graphic structure.",
    "exampleImage": "https://images.unsplash.com/photo-1547887538-e3a2f32cb1cc?w=600&q=85"
  },
  {
    "id": "campaign-campaign-model-portrait",
    "category": "Campaign",
    "name": "Campaign Model Portrait",
    "description": "A close or mid-length portrait of a model wearing the garment, focused on attitude, identity and brand expression.",
    "exampleImage": "https://images.unsplash.com/photo-1496747611176-843222e1e57c?w=600&q=85"
  },
  {
    "id": "campaign-movement-campaign-image",
    "category": "Campaign",
    "name": "Movement Campaign Image",
    "description": "A dynamic campaign image using movement, motion, fabric flow or an expressive pose.",
    "exampleImage": "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=600&q=85"
  },
  {
    "id": "campaign-seasonal-campaign-image",
    "category": "Campaign",
    "name": "Seasonal Campaign Image",
    "description": "A branded image built around a seasonal collection, occasion or cultural moment.",
    "exampleImage": "https://images.unsplash.com/photo-1483985988355-763728e1935b?w=600&q=85"
  },
  {
    "id": "campaign-collection-story",
    "category": "Campaign",
    "name": "Collection Story",
    "description": "An image presenting multiple garments or coordinated looks as part of one collection narrative.",
    "exampleImage": "https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=600&q=85"
  },
  {
    "id": "campaign-product-world-still-life",
    "category": "Campaign",
    "name": "Product World Still Life",
    "description": "A carefully art-directed still life combining the garment with relevant materials, objects, surfaces or accessories.",
    "exampleImage": "https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=600&q=85"
  },
  {
    "id": "campaign-statement-image",
    "category": "Campaign",
    "name": "Statement Image",
    "description": "A visually striking campaign asset built around one memorable image, gesture, composition or visual idea.",
    "exampleImage": "https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?w=600&q=85"
  },
  {
    "id": "campaign-promotional-campaign-asset",
    "category": "Campaign",
    "name": "Promotional Campaign Asset",
    "description": "A branded image designed to support a specific commercial message such as a launch, collection, offer or availability announcement.",
    "exampleImage": "https://images.unsplash.com/photo-1525507119028-ed4c629a60a3?w=600&q=85"
  }
];

export const OUTERWEAR_ECOMMERCE_RECIPES: readonly OutputRecipe[] = [
  {
    id: 'ecommerce-outerwear-front-close',
    category: 'Ecommerce',
    name: 'Front Close',
    description: 'A tight product-only crop of the upper front, showing the neckline, front construction and visible details.',
    exampleImage: '/output-examples/outerwear/01-front-close.png',
  },
  {
    id: 'ecommerce-outerwear-front-medium',
    category: 'Ecommerce',
    name: 'Front Medium',
    description: 'The complete outerwear piece shown from the front, with sleeves and hem visible and little surrounding space.',
    exampleImage: '/output-examples/outerwear/02-front-medium.png',
  },
  {
    id: 'ecommerce-outerwear-over-the-shoulder',
    category: 'Ecommerce',
    name: 'Over-the-Shoulder (No Face)',
    description: 'A close rear three-quarter view of the outerwear being worn, focusing on the shoulder, collar and upper-back construction with no face visible.',
    exampleImage: '/output-examples/outerwear/03-over-the-shoulder-no-face.png',
  },
  {
    id: 'ecommerce-outerwear-full-body-model',
    category: 'Ecommerce',
    name: 'Full Body with Model (No Face)',
    description: 'The outerwear worn as part of a complete outfit, framed from the base of the neck to the feet with no face visible.',
    exampleImage: '/output-examples/outerwear/04-full-body-model-no-face.png',
  },
  {
    id: 'ecommerce-outerwear-close-up',
    category: 'Ecommerce',
    name: 'Close-Up',
    description: 'A close crop highlighting a seam, fastening or other visible construction detail of the outerwear.',
    exampleImage: '/output-examples/outerwear/05-construction-close-up.png',
  },
  {
    id: 'ecommerce-outerwear-back',
    category: 'Ecommerce',
    name: 'Back',
    description: 'A complete product-only rear view showing the outerwear’s back silhouette and construction.',
    exampleImage: '/output-examples/outerwear/06-back-product.png',
  },
  {
    id: 'ecommerce-outerwear-front-model',
    category: 'Ecommerce',
    name: 'Front with Model (No Face)',
    description: 'A front view of the outerwear being worn, framed closely around the garment from the base of the neck with no face visible.',
    exampleImage: '/output-examples/outerwear/07-front-model-no-face.png',
  },
  {
    id: 'ecommerce-outerwear-back-model',
    category: 'Ecommerce',
    name: 'Back with Model (No Face)',
    description: 'A rear view of the outerwear being worn, framed closely around the garment to show its fit and drape with no face visible.',
    exampleImage: '/output-examples/outerwear/08-back-model-no-face.png',
  },
  {
    id: 'ecommerce-outerwear-side-angle-model',
    category: 'Ecommerce',
    name: 'Side / Angled with Model (No Face)',
    description: 'A side or three-quarter view of the outerwear being worn, showing its depth, silhouette and fit with no face visible.',
    exampleImage: '/output-examples/outerwear/09-side-angle-model-no-face.png',
  },
  {
    id: 'ecommerce-outerwear-fabric',
    category: 'Ecommerce',
    name: 'Fabric Shot',
    description: 'A macro view of the outerwear’s material texture and surface finish, keeping hardware and construction details out of focus.',
    exampleImage: '/output-examples/outerwear/10-fabric-leather-texture.png',
  },
];

export const FOOTWEAR_ECOMMERCE_RECIPES: readonly OutputRecipe[] = [
  {
    id: 'ecommerce-footwear-three-quarter-product',
    category: 'Ecommerce',
    name: 'Three-Quarter Product',
    description: 'An angled product-only view showing the footwear’s front, outer side and overall shape against a simple background.',
    exampleImage: '/output-examples/footwear/01-three-quarter-product.png',
  },
  {
    id: 'ecommerce-footwear-outer-side',
    category: 'Ecommerce',
    name: 'Outer Side',
    description: 'A straight-on outer-side profile showing the complete silhouette, upper construction and sole shape.',
    exampleImage: '/output-examples/footwear/02-outer-side.png',
  },
  {
    id: 'ecommerce-footwear-inner-side',
    category: 'Ecommerce',
    name: 'Inner Side',
    description: 'A straight-on inner-side profile showing the footwear’s medial construction and visible details.',
    exampleImage: '/output-examples/footwear/03-inner-side.png',
  },
  {
    id: 'ecommerce-footwear-front-view',
    category: 'Ecommerce',
    name: 'Front View',
    description: 'A head-on product view showing the toe shape, front proportions and visible upper details.',
    exampleImage: '/output-examples/footwear/04-front-view.png',
  },
  {
    id: 'ecommerce-footwear-rear-view',
    category: 'Ecommerce',
    name: 'Rear View',
    description: 'A straight-on rear view showing the heel shape, back construction and sole thickness.',
    exampleImage: '/output-examples/footwear/05-rear-view.png',
  },
  {
    id: 'ecommerce-footwear-top-view',
    category: 'Ecommerce',
    name: 'Top View',
    description: 'A direct overhead view showing the footwear’s shape from toe to heel, including its opening and visible fastenings.',
    exampleImage: '/output-examples/footwear/06-top-view.png',
  },
  {
    id: 'ecommerce-footwear-sole-view',
    category: 'Ecommerce',
    name: 'Sole View',
    description: 'A complete underside view showing the outsole shape, tread and visible construction from heel to toe.',
    exampleImage: '/output-examples/footwear/07-sole-view.png',
  },
  {
    id: 'ecommerce-footwear-material-and-detail',
    category: 'Ecommerce',
    name: 'Material and Detail',
    description: 'A close crop highlighting the footwear’s material texture, surface finish and visible stitching or construction details.',
    exampleImage: '/output-examples/footwear/08-material-and-detail.png',
  },
  {
    id: 'ecommerce-footwear-front-on-feet',
    category: 'Ecommerce',
    name: 'Front on Feet',
    description: 'The footwear worn by an adult in a natural front-facing stance, with both feet visible and the frame cropped below the knees.',
    exampleImage: '/output-examples/footwear/09-front-on-feet.png',
  },
  {
    id: 'ecommerce-footwear-side-on-feet',
    category: 'Ecommerce',
    name: 'Side on Feet',
    description: 'The footwear worn by an adult in a natural side stance, showing its profile and fit with the frame cropped below the knees.',
    exampleImage: '/output-examples/footwear/10-side-on-feet.png',
  },
];

export const SOCKS_ECOMMERCE_RECIPES: readonly OutputRecipe[] = [
  {
    id: 'ecommerce-socks-three-quarter-on-feet',
    category: 'Ecommerce',
    name: 'Three-Quarter on Feet',
    description: 'The socks worn by an adult in a natural three-quarter stance, showing both feet and visible lower legs above the cuffs, with no footwear and the frame cropped below the knees.',
    exampleImage: '/output-examples/socks/01-three-quarter-on-feet.png',
  },
  {
    id: 'ecommerce-socks-rear-on-feet',
    category: 'Ecommerce',
    name: 'Rear on Feet',
    description: 'A rear view of socks worn by an adult, showing their heel shape and visible lower legs above the cuffs, with no footwear and the frame cropped below the knees.',
    exampleImage: '/output-examples/socks/03-rear-on-feet.png',
  },
  {
    id: 'ecommerce-socks-folded-product',
    category: 'Ecommerce',
    name: 'Folded Product',
    description: 'Neatly fold the socks on a plain surface, keeping their colour and distinctive design visible.',
    exampleImage: '/output-examples/socks/10-folded-product.png',
  },
  {
    id: 'ecommerce-socks-flat-lay',
    category: 'Ecommerce',
    name: 'Flat Lay',
    description: 'The socks arranged naturally on a plain surface and photographed from directly above to show their complete shape and pattern.',
    exampleImage: '/output-examples/socks/04-flat-lay.png',
  },
  {
    id: 'ecommerce-socks-heel-detail',
    category: 'Ecommerce',
    name: 'Heel Detail',
    description: 'A close crop highlighting the sock’s heel shape, knit texture and visible construction details.',
    exampleImage: '/output-examples/socks/06-heel-detail.png',
  },
  {
    id: 'ecommerce-socks-knit-texture',
    category: 'Ecommerce',
    name: 'Knit Texture',
    description: 'A macro view of the sock’s actual knit pattern, yarn texture and surface finish, keeping its material and colour consistent.',
    exampleImage: '/output-examples/socks/08-knit-texture.png',
  },
  {
    id: 'ecommerce-socks-front-on-feet',
    category: 'Ecommerce',
    name: 'Front on Feet',
    description: 'The socks worn by an adult in a natural front-facing stance, with both feet visible, no footwear and the frame cropped below the knees.',
    exampleImage: '/output-examples/socks/09-front-on-feet.png',
  },
  {
    id: 'ecommerce-socks-heel-detail-on-foot',
    category: 'Ecommerce',
    name: 'Heel Detail on Foot',
    description: 'A close rear three-quarter view of a sock on an adult foot, emphasizing the heel construction while showing bare lower-leg skin above the cuff, with no footwear and the frame cropped below the knee.',
    exampleImage: '/output-examples/socks/06-heel-detail-on-foot.png',
  },
];

const outerwearOutputRecipes: readonly OutputRecipe[] = [
  ...OUTERWEAR_ECOMMERCE_RECIPES,
  ...OUTPUT_RECIPES.filter(recipe => recipe.category !== 'Ecommerce'),
];

const footwearOutputRecipes: readonly OutputRecipe[] = [
  ...FOOTWEAR_ECOMMERCE_RECIPES,
  ...OUTPUT_RECIPES.filter(recipe => recipe.category !== 'Ecommerce'),
];

const socksOutputRecipes: readonly OutputRecipe[] = [
  ...SOCKS_ECOMMERCE_RECIPES,
  ...OUTPUT_RECIPES.filter(recipe => recipe.category !== 'Ecommerce'),
];

export function getOutputRecipes(productCategory?: string | null): readonly OutputRecipe[] {
  const category = productCategory?.trim().toLowerCase();
  if (category === 'outerwear') return outerwearOutputRecipes;
  if (category === 'footwear') return footwearOutputRecipes;
  if (category === 'socks') return socksOutputRecipes;
  return OUTPUT_RECIPES;
}
