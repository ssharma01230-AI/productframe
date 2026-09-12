"""Category and channel rules for product understanding and generation."""
import re
from dataclasses import dataclass
from typing import Final

from .category_schemas import CATEGORY_DETAIL_MODELS


TOPS_FAMILY_SUBTYPE_MAP: Final[dict[str, str]] = {
    "shirt": "shirts",
    "button-down shirt": "shirts",
    "overshirt": "shirts",
    "t-shirt": "t-shirts-casual-tops",
    "graphic tee": "t-shirts-casual-tops",
    "polo shirt": "t-shirts-casual-tops",
    "henley": "t-shirts-casual-tops",
    "tank top": "sleeveless-tops",
    "camisole": "sleeveless-tops",
    "tube top": "sleeveless-tops",
    "vest top": "sleeveless-tops",
    "jumper": "knitwear",
    "sweater": "knitwear",
    "cardigan": "knitwear",
    "sweatshirt": "knitwear",
    "pullover hoodie": "hoodies",
    "zip-through hoodie": "hoodies",
    "zip-up hoodie": "hoodies",
    "hoodie": "hoodies",
    "hooded sweatshirt": "hoodies",
}


def get_tops_family_for_subtype(subtype: str | None) -> str | None:
    """Return the controlled Tops family from an exact or descriptive subtype.

    Recognition deliberately keeps a descriptive subtype (for example,
    ``zip-up hoodie with drawstring hood``), so family routing cannot rely only
    on an exact dictionary lookup.
    """
    if not subtype or not isinstance(subtype, str):
        return None
    normalized = " ".join(subtype.strip().lower().split())
    exact = TOPS_FAMILY_SUBTYPE_MAP.get(normalized)
    if exact:
        return exact

    # Prefer explicit construction signals before broader words such as
    # ``sweater`` or ``shirt``. This keeps a sweater vest in Sleeveless Tops.
    if re.search(r"\b(?:sleeveless|tank|camisole|tube|vest)\b", normalized):
        return "sleeveless-tops"
    if re.search(r"\b(?:hoodie|hooded)\b", normalized):
        return "hoodies"
    if re.search(r"\b(?:t[- ]shirt|tee|polo|henley)\b", normalized):
        return "t-shirts-casual-tops"
    if re.search(r"\b(?:knit|knitted|knitwear|jumper|sweater|cardigan|sweatshirt)\b", normalized):
        return "knitwear"
    if re.search(r"\b(?:shirt|blouse|tunic|overshirt)\b", normalized):
        return "shirts"
    return None


BOTTOMS_FAMILY_SUBTYPE_MAP: Final[dict[str, str]] = {
    "jeans": "structured_bottoms",
    "trousers": "structured_bottoms",
    "chinos": "structured_bottoms",
    "cargo trousers": "structured_bottoms",
    "shorts": "shorts",
    "joggers": "casual_bottoms",
    "leggings": "leggings",
    "skirt": "skirts",
}


CONTROLLED_FAMILY_LABELS: Final[dict[str, str]] = {
    "shirts": "Shirt", "t-shirts-casual-tops": "T-Shirt", "sleeveless-tops": "Sleeveless Top", "knitwear": "Knitwear", "hoodies": "Hoodie",
    "jackets": "Jacket", "coats": "Coat", "gilets-padded-vests": "Gilet",
    "structured_bottoms": "Trousers", "shorts": "Shorts", "casual_bottoms": "Joggers", "leggings": "Leggings", "skirts": "Skirt",
    "dresses": "Dress", "tailored-jackets": "Tailored Jacket", "waistcoats": "Waistcoat", "suits": "Suit", "tuxedos": "Tuxedo",
    "pyjamas": "Pyjamas", "nightwear": "Nightwear", "robes": "Robe",
    "lower_body_underwear": "Lower-Body Underwear", "bra": "Bra", "lingerie": "Lingerie", "base_layer": "Base Layer", "underwear_set": "Underwear Set",
    "socks": "Socks", "trainers": "Trainers", "flats-loafers": "Flats / Loafers", "sandals-open-shoes": "Sandals", "boots": "Boots", "heels": "Heels",
    "rings": "Rings", "bracelets": "Bracelets", "earrings": "Earrings", "necklaces": "Necklace", "watches": "Watches",
    "headwear": "Headwear", "scarves": "Scarf", "gloves": "Gloves", "belts": "Belt", "ties-neckwear": "Neckwear", "veils": "Veil",
}


def controlled_subtype_label(*, category: str | None, family: str | None, subtype: str | None, product_type: str | None = None) -> str:
    """Return a short controlled label, never the descriptive product type."""
    normalized_family = " ".join(family.strip().lower().split()) if isinstance(family, str) and family.strip() else None
    if normalized_family in CONTROLLED_FAMILY_LABELS:
        return CONTROLLED_FAMILY_LABELS[normalized_family]
    value = " ".join((subtype or "").strip().lower().split())
    patterns = (
        ("t-shirt", "T-Shirt"), ("tee", "T-Shirt"), ("shirt", "Shirt"), ("hoodie", "Hoodie"),
        ("pump", "Pumps"), ("heel", "Heels"), ("trainer", "Trainers"), ("sneaker", "Trainers"), ("boot", "Boots"), ("sandal", "Sandals"), ("loafer", "Flats / Loafers"),
        ("jogger", "Joggers"), ("sweatpant", "Joggers"), ("legging", "Leggings"), ("short", "Shorts"), ("skirt", "Skirt"), ("trouser", "Trousers"), ("jean", "Jeans"),
        ("jacket", "Jacket"), ("coat", "Coat"), ("dress", "Dress"), ("scarf", "Scarf"), ("glove", "Gloves"), ("belt", "Belt"), ("ring", "Rings"), ("bracelet", "Bracelets"), ("earring", "Earrings"), ("necklace", "Necklace"), ("watch", "Watches"),
    )
    for needle, label in patterns:
        if needle in value:
            return label
    if value and len(value.split()) <= 3:
        return value.title()
    return "Unclassified"


def get_bottoms_family_for_subtype(subtype: str | None) -> str | None:
    """Return the controlled rendering family for a bottoms subtype."""
    if not subtype or not isinstance(subtype, str):
        return None
    normalized = " ".join(subtype.strip().lower().split())
    exact = BOTTOMS_FAMILY_SUBTYPE_MAP.get(normalized)
    if exact:
        return exact
    # Vision often returns descriptive subtypes such as "wide leg drawstring
    # pants" rather than the controlled leaf "joggers". Preserve the intended
    # casual-bottoms route when elastic/drawstring lounge construction is clear.
    if any(signal in normalized for signal in ("jogger", "sweatpant", "sweat pant")):
        return "casual_bottoms"
    if "drawstring" in normalized and any(signal in normalized for signal in ("pant", "bottom", "trouser")):
        return "casual_bottoms"
    return None


@dataclass(frozen=True, slots=True)
class ChannelDefinition:
    id: str
    name: str
    description: str
    prompt_rules: tuple[str, ...]
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class CategoryDefinition:
    id: str
    name: str
    subtypes: tuple[str, ...]
    required_analysis_fields: tuple[str, ...]
    optional_analysis_fields: tuple[str, ...]
    prompt_rules: tuple[str, ...]
    supported_channels: tuple[str, ...]


CHANNELS: Final[dict[str, ChannelDefinition]] = {
    "ecommerce": ChannelDefinition(
        id="ecommerce",
        name="Ecommerce",
        description="Clear product presentation for catalogue and product pages.",
        prompt_rules=(
            "Prioritise accurate product identity over styling.",
            "Show the requested product clearly and keep the background controlled.",
            "Do not add props, extra products, branding or unsupported details.",
        ),
    ),
    "lifestyle": ChannelDefinition(
        id="lifestyle",
        name="Lifestyle",
        description="Product shown in a realistic use or styling context.",
        prompt_rules=(
            "Keep the selected product identity unchanged while allowing the requested context.",
            "Do not let models, locations or styling obscure important product details.",
        ),
    ),
    "campaign": ChannelDefinition(
        id="campaign",
        name="Campaign",
        description="Art-directed content with a stronger visual concept.",
        prompt_rules=(
            "The visual concept may be expressive, but the product identity remains authoritative.",
            "Do not change product-defining colour, construction or branding.",
        ),
    ),
}

_COMMON_REQUIRED = (
    "product_name",
    "category",
    "product_type",
    "global_details.colour",
    "global_details.materials",
    "global_details.construction",
    "global_details.branding",
    "global_details.gender",
    "confidence_details",
)
_COMMON_OPTIONAL = (
    "global_details.gender.user_confirmed",
    "global_details.branding.graphics",
    "global_details.branding.logos",
)

CATEGORIES: Final[dict[str, CategoryDefinition]] = {
    "tops": CategoryDefinition(
        id="tops", name="Tops",
        subtypes=tuple(TOPS_FAMILY_SUBTYPE_MAP),
        required_analysis_fields=_COMMON_REQUIRED + ("category_details", "category_details.neckline_type", "category_details.sleeve_type", "category_details.fit_and_silhouette"),
        optional_analysis_fields=_COMMON_OPTIONAL + ("category_details.hood_details", "category_details.pocket_details", "category_details.collar_thickness", "category_details.body_width_relative_to_length", "category_details.graphic_condition"),
        prompt_rules=(
            "Preserve neckline, sleeves, shoulder shape, hem, fit, length and fabric texture.",
            "Preserve collar construction, relative proportions, drape, wrinkles, wash, fading and graphic condition when visible.",
            "Do not turn a V-neck into a crew neck or change sleeve length.",
        ),
        supported_channels=tuple(CHANNELS),
    ),
    "outerwear": CategoryDefinition(
        id="outerwear", name="Outerwear",
        subtypes=("coat", "jacket", "blazer", "waistcoat", "parka", "gilet", "bomber", "trench coat", "raincoat", "puffer"),
        required_analysis_fields=_COMMON_REQUIRED + ("category_details", "category_details.closure_type", "category_details.fit_and_silhouette"),
        optional_analysis_fields=_COMMON_OPTIONAL + ("category_details.hood_type", "category_details.padding_or_insulation", "category_details.collar_or_lapel", "category_details.panel_and_seam_details", "category_details.hardware_details"),
        prompt_rules=("Preserve outerwear structure, closures, panels, pockets, hardware, lining and material weight.", "Do not invent hidden back construction or weather-protection performance."),
        supported_channels=tuple(CHANNELS),
    ),
    "bottoms": CategoryDefinition(
        id="bottoms", name="Bottoms",
        subtypes=("shorts", "skirt", "leggings", "trousers", "jeans", "cargo trousers", "joggers", "chinos"),
        required_analysis_fields=_COMMON_REQUIRED + (
            "category_details",
            "category_details.waistband_type",
            "category_details.waist_height",
            "category_details.fly_or_closure",
            "category_details.leg_shape",
            "category_details.leg_width",
            "category_details.garment_length",
            "category_details.hem_details",
            "category_details.fit_and_silhouette",
        ),
        optional_analysis_fields=_COMMON_OPTIONAL + (
            "category_details.pocket_details",
            "category_details.pleats_or_darts",
            "category_details.belt_loops",
            "category_details.panel_or_seam_details",
            "category_details.visible_uncertainties",
        ),
        prompt_rules=(
            "Preserve waistband, waist height, rise, closure, leg shape, leg width, garment length, hem, pockets and fit.",
            "For model-worn outputs, keep the framing from the waist or lower midsection downward and do not let styling obscure the bottoms.",
            "For folded and construction-detail outputs, show the product naturally supported by the specified surface and do not invent hidden construction.",
        ),
        supported_channels=tuple(CHANNELS),
    ),
    "underwear": CategoryDefinition(
        id="underwear", name="Underwear",
        subtypes=("lingerie", "boxers", "briefs", "bikini briefs", "bra", "bralette", "vest", "undershirt"),
        required_analysis_fields=_COMMON_REQUIRED + ("category_details", "category_details.coverage", "category_details.fit_and_silhouette"),
        optional_analysis_fields=_COMMON_OPTIONAL + ("category_details.support_details", "category_details.cup_shape"),
        prompt_rules=("Do not infer body measurements, size or support level.",),
        supported_channels=tuple(CHANNELS),
    ),
    "socks": CategoryDefinition(
        id="socks", name="Socks",
        subtypes=("normal", "running", "ankle", "trainer", "crew", "knee-high", "stockings", "compression", "thermal"),
        required_analysis_fields=_COMMON_REQUIRED + ("category_details", "category_details.sock_length", "category_details.cuff_details"),
        optional_analysis_fields=_COMMON_OPTIONAL + ("category_details.compression_features", "category_details.padding", "category_details.leg_width", "category_details.ribbing_or_knit", "category_details.seam_details"),
        prompt_rules=("Preserve sock length, cuff, heel, toe, knit pattern, stretch and reinforcement details.", "Do not invent hidden foot or leg construction."),
        supported_channels=tuple(CHANNELS),
    ),
    "footwear": CategoryDefinition(
        id="footwear", name="Footwear",
        subtypes=("heels", "trainers", "sandals", "crocs", "boots", "loafers", "flats", "sliders", "mules"),
        required_analysis_fields=_COMMON_REQUIRED + ("category_details", "category_details.toe_shape", "category_details.sole_type"),
        optional_analysis_fields=_COMMON_OPTIONAL + ("category_details.heel_type", "category_details.laces_or_straps", "category_details.outsole_tread", "category_details.collar_or_opening"),
        prompt_rules=("Preserve toe shape, sole, panels, fastenings, hardware, tread and upper material.", "Do not invent the unseen underside or internal fit."),
        supported_channels=tuple(CHANNELS),
    ),
    "scarves": CategoryDefinition("scarves", "Scarves and Shawls", ("scarf", "shawl", "stole", "wrap", "snood"), _COMMON_REQUIRED + ("category_details", "category_details.scarf_shape"), _COMMON_OPTIONAL, ("Preserve shape, edge finish, pattern, texture and drape.",), tuple(CHANNELS)),
    "gloves": CategoryDefinition("gloves", "Gloves and Mittens", ("gloves", "mittens", "fingerless gloves", "winter gloves"), _COMMON_REQUIRED + ("category_details", "category_details.finger_configuration"), _COMMON_OPTIONAL, ("Preserve finger configuration, cuffs, seams, grip and insulation.",), tuple(CHANNELS)),
    "headwear": CategoryDefinition("headwear", "Headwear", ("baseball cap", "cap", "beanie", "bucket hat", "fedora", "sun hat", "visor", "beret", "fascinator", "headband"), _COMMON_REQUIRED + ("category_details", "category_details.crown_shape"), _COMMON_OPTIONAL + ("category_details.brim_or_peak_shape", "category_details.closure_or_adjustment"), ("Preserve crown, brim or peak, structure, surface texture, fit and visible adjustment details.",), tuple(CHANNELS)),
    "rings": CategoryDefinition("rings", "Rings", ("ring", "band", "signet ring"), _COMMON_REQUIRED + ("category_details", "category_details.jewellery_form"), _COMMON_OPTIONAL + ("category_details.stone_or_decoration_details",), ("Preserve visible ring form, setting, stones, finish and hardware without inferring exact materials or carat.",), tuple(CHANNELS)),
    "bracelets": CategoryDefinition("bracelets", "Bracelets", ("bracelet", "bangle", "cuff bracelet", "chain bracelet"), _COMMON_REQUIRED + ("category_details", "category_details.jewellery_form"), _COMMON_OPTIONAL + ("category_details.chain_or_band_details",), ("Preserve visible bracelet form, chain or band structure, setting, finish and hardware without inferring exact materials or carat.",), tuple(CHANNELS)),
    "earrings": CategoryDefinition("earrings", "Earrings", ("earrings", "stud earrings", "hoop earrings", "drop earrings", "ear cuff"), _COMMON_REQUIRED + ("category_details", "category_details.jewellery_form"), _COMMON_OPTIONAL + ("category_details.stone_or_decoration_details",), ("Preserve visible earring form, setting, stones, attachment and finish without inferring exact materials or carat.",), tuple(CHANNELS)),
    "watches": CategoryDefinition("watches", "Watches", ("watch", "analogue watch", "digital watch", "smartwatch", "pocket watch"), _COMMON_REQUIRED + ("category_details", "category_details.case_shape"), _COMMON_OPTIONAL, ("Preserve visible dial, case, strap and hardware details.",), tuple(CHANNELS)),
    "belts": CategoryDefinition("belts", "Belts", ("leather belt", "canvas belt", "webbing belt", "dress belt", "utility belt", "fashion belt", "chain belt", "waist belt", "braided belt"), _COMMON_REQUIRED + ("category_details", "category_details.belt_type", "category_details.buckle_type"), _COMMON_OPTIONAL, ("Preserve strap, buckle, holes, hardware, finish and proportions.",), tuple(CHANNELS)),
    "neckwear": CategoryDefinition("neckwear", "Ties and Neckwear", ("tie", "neck tie", "bow tie", "cravat", "ascot"), _COMMON_REQUIRED + ("category_details", "category_details.shape"), _COMMON_OPTIONAL, ("Preserve shape, length, width, knot or fastening, edge finish, pattern and drape.",), tuple(CHANNELS)),
    "dresses": CategoryDefinition(
        "dresses", "Dresses", ("dress",),
        _COMMON_REQUIRED + ("category_details", "category_details.structure", "category_details.length", "category_details.silhouette"),
        _COMMON_OPTIONAL + ("category_details.occasion",),
        ("Preserve the dress silhouette, length, structure, drape and visible construction.",), tuple(CHANNELS),
    ),
    "tailoring": CategoryDefinition(
        "tailoring", "Tailoring", ("blazer", "sport coat", "dinner jacket", "waistcoat", "suit", "tuxedo"),
        _COMMON_REQUIRED + ("category_details", "category_details.product_unit", "category_details.fit_and_silhouette"),
        _COMMON_OPTIONAL + ("category_details.lapel_or_neckline",),
        ("Distinguish standalone tailored garments from coordinated suit products; preserve structure and fit.",), tuple(CHANNELS),
    ),
    "sleepwear_loungewear": CategoryDefinition(
        "sleepwear_loungewear", "Sleepwear and Loungewear", ("pyjama set", "pyjama top", "pyjama bottom", "nightshirt", "nightgown", "robe"),
        _COMMON_REQUIRED + ("category_details", "category_details.product_unit", "category_details.fit_and_silhouette"),
        _COMMON_OPTIONAL,
        ("Preserve coverage, comfort-oriented construction, fabric appearance and whether the product is a set or single item.",), tuple(CHANNELS),
    ),
    "jewellery": CategoryDefinition(
        "jewellery", "Jewellery", ("ring", "band", "signet ring", "bracelet", "bangle", "cuff bracelet", "chain bracelet", "stud earring", "hoop earring", "drop earring", "ear cuff", "necklace", "pendant", "choker", "locket", "analogue watch", "digital watch", "smartwatch", "pocket watch"),
        _COMMON_REQUIRED + ("category_details", "category_details.form"),
        _COMMON_OPTIONAL,
        ("Preserve visible jewellery form, setting, stones, finish and hardware without inferring exact materials or carat.",), tuple(CHANNELS),
    ),
    "accessories": CategoryDefinition(
        "accessories", "Accessories", ("cap", "baseball cap", "beanie", "bucket hat", "fedora", "sun hat", "visor", "beret", "fascinator", "headband", "scarf", "shawl", "stole", "wrap", "snood", "glove", "mitten", "fingerless glove", "belt", "tie", "bow tie", "cravat", "ascot", "veil"),
        _COMMON_REQUIRED + ("category_details", "category_details.form"),
        _COMMON_OPTIONAL + ("category_details.occasion",),
        ("Preserve the accessory form, proportions, material, fastening and visible finish.",), tuple(CHANNELS),
    ),
    # Bags are intentionally not represented: they are outside the supported clothing scope.
}


def get_category_definition(category: str) -> CategoryDefinition:
    try:
        return CATEGORIES[category.strip().lower()]
    except KeyError as exc:
        raise ValueError(f"Unsupported product category: {category}") from exc


def get_channel_definition(channel: str) -> ChannelDefinition:
    try:
        return CHANNELS[channel.strip().lower()]
    except KeyError as exc:
        raise ValueError(f"Unsupported output channel: {channel}") from exc


def validate_category_channel(category: str, channel: str) -> None:
    definition = get_category_definition(category)
    channel_definition = get_channel_definition(channel)
    if not channel_definition.enabled or channel_definition.id not in definition.supported_channels:
        raise ValueError(f"Channel {channel} is not available for category {category}")


def validate_category_details(category: str, details: object) -> dict[str, object]:
    definition = get_category_definition(category)
    model = CATEGORY_DETAIL_MODELS[definition.id]
    return model.model_validate(details).model_dump()
