"""Category-specific visual schemas used by product recognition."""
from typing import Literal, Union

from pydantic import BaseModel, Field


TopsFamily = Literal[
    "shirts", "t-shirts-casual-tops", "sleeveless-tops", "knitwear", "hoodies"
]
OuterwearFamily = Literal["jackets", "coats", "gilets-padded-vests"]
DressFamily = Literal["dresses"]
TailoringFamily = Literal["tailored-jackets", "waistcoats", "suits", "tuxedos"]
SleepwearFamily = Literal["pyjamas", "nightwear", "robes"]
SocksFamily = Literal["socks"]
FootwearFamily = Literal["trainers", "flats-loafers", "sandals-open-shoes", "boots", "heels"]
JewelleryFamily = Literal["rings", "bracelets", "earrings", "necklaces", "watches"]
AccessoriesFamily = Literal["headwear", "scarves", "gloves", "belts", "ties-neckwear", "veils"]


class TopsDetails(BaseModel):
    family: TopsFamily | None = None
    subtype: str
    neckline_type: str
    neckline_depth: str
    collar_type: str
    sleeve_type: str
    sleeve_length: str
    sleeve_width: str
    shoulder_shape: str
    cuff_details: str
    hem_shape: str
    fit_and_silhouette: str
    garment_length: str
    closure_details: list[str]
    pocket_details: list[str]
    hood_details: list[str]
    visible_uncertainties: list[str]
    collar_thickness: str = "not_visible"
    collar_width: str = "not_visible"
    neckline_rigidity: str = "not_visible"
    body_width_relative_to_length: str = "not_visible"
    shoulder_drop: str = "not_visible"
    silhouette_volume: str = "not_visible"
    sleeve_width_relative_to_body: str = "not_visible"
    hem_position: str = "not_visible"
    drape_quality: str = "not_visible"
    rigidity_level: str = "not_visible"
    wrinkle_visibility: str = "not_visible"
    surface_softness: str = "not_visible"
    fabric_body: str = "not_visible"
    wash_treatment: str = "not_visible"
    fade_level: str = "not_visible"
    graphic_condition: str = "not_visible"
    graphic_scale: str = "not_visible"
    graphic_placement: str = "not_visible"
    graphic_edge_quality: str = "not_visible"


class OuterwearDetails(BaseModel):
    family: OuterwearFamily | None = None
    subtype: str
    collar_or_lapel: str
    hood_type: str
    sleeve_type: str
    sleeve_length: str
    closure_type: str
    fastening_details: list[str]
    pocket_details: list[str]
    lining_details: str
    padding_or_insulation: str
    fabric_weight: str
    garment_length: str
    fit_and_silhouette: str
    hem_shape: str
    cuff_details: str
    weather_protection_features: list[str]
    shoulder_shape: str = "not_visible"
    panel_and_seam_details: list[str] = []
    fabric_texture: str = "not_visible"
    surface_finish: str = "not_visible"
    hardware_details: list[str] = []
    drape_and_rigidity: str = "not_visible"
    visible_uncertainties: list[str]


BottomsFamily = Literal[
    "structured_bottoms", "shorts", "casual_bottoms", "leggings", "skirts"
]


class BottomsDetails(BaseModel):
    family: BottomsFamily | None = None
    subtype: str
    waistband_type: str
    waist_height: str
    fly_or_closure: str
    leg_shape: str
    leg_width: str
    garment_length: str
    hem_details: str
    pocket_details: list[str]
    pleats_or_darts: list[str]
    belt_loops: str
    panel_or_seam_details: list[str]
    fit_and_silhouette: str
    visible_uncertainties: list[str]
    # Shorts-specific observations; remain not_visible for other bottoms.
    inseam_length: str = "not_visible"
    leg_opening: str = "not_visible"
    drawcord_details: str = "not_visible"
    shorts_length: str = "not_visible"


UnderwearFamily = Literal[
    "lower_body_underwear", "bra", "lingerie", "base_layer", "underwear_set"
]


class LowerBodyUnderwearDetails(BaseModel):
    pouch_or_front_construction: str = "not_applicable"
    fly_details: str = "not_applicable"
    leg_length_and_opening: str = "not_applicable"
    gusset_details: str = "not_applicable"
    side_coverage: str = "not_applicable"


class BraDetails(BaseModel):
    cup_construction: str = "not_applicable"
    strap_construction: str = "not_applicable"
    band_construction: str = "not_applicable"
    support_structure: str = "not_applicable"
    fastening_details: list[str] = Field(default_factory=list)


class LingerieDetails(BaseModel):
    lace_or_mesh_details: str = "not_applicable"
    panel_details: list[str] = Field(default_factory=list)
    decorative_trim_details: list[str] = Field(default_factory=list)
    shaping_or_boning_details: str = "not_applicable"


class BaseLayerDetails(BaseModel):
    neckline_or_opening: str = "not_applicable"
    strap_or_sleeve_details: str = "not_applicable"
    hem_details: str = "not_applicable"
    layering_fit: str = "not_applicable"


class UnderwearSetDetails(BaseModel):
    piece_count: str = "not_applicable"
    coordinated_piece_details: list[str] = Field(default_factory=list)
    matching_features: list[str] = Field(default_factory=list)


class UnderwearDetails(BaseModel):
    """Stable underwear core with optional family-specific detail groups."""

    family: UnderwearFamily | None = None
    subtype: str
    coverage: str
    waist_height: str
    rise: str
    elastic_details: str
    fabric_appearance: str
    fit_and_silhouette: str
    visible_uncertainties: list[str]
    # These attributes are retained for compatibility but are explicitly
    # non-applicable by default rather than being required for every family.
    strap_type: str = "not_applicable"
    strap_width: str = "not_applicable"
    support_details: str = "not_applicable"
    cup_shape: str = "not_applicable"
    closure_details: list[str] = Field(default_factory=list)
    seam_details: list[str] = Field(default_factory=list)
    lower_body: LowerBodyUnderwearDetails | None = None
    bra: BraDetails | None = None
    lingerie: LingerieDetails | None = None
    base_layer: BaseLayerDetails | None = None
    set_details: UnderwearSetDetails | None = None


class SocksDetails(BaseModel):
    family: SocksFamily | None = None
    subtype: str
    sock_length: str
    cuff_height: str
    cuff_details: str
    toe_shape: str
    heel_details: str
    toe_and_heel_reinforcement: str
    padding: str
    ribbing_or_knit: str
    compression_features: list[str]
    pattern: str
    fit_and_silhouette: str
    leg_width: str = "not_visible"
    foot_shape: str = "not_visible"
    fabric_appearance: str = "not_visible"
    stretch_or_flexibility: str = "not_visible"
    seam_details: list[str] = []
    graphic_or_branding_details: list[str] = []
    visible_uncertainties: list[str]


class FootwearDetails(BaseModel):
    family: FootwearFamily | None = None
    subtype: str
    toe_shape: str
    heel_type: str
    heel_height_appearance: str
    sole_type: str
    sole_thickness: str
    upper_material_appearance: str
    panel_details: list[str]
    closure_type: str
    laces_or_straps: list[str]
    buckle_details: list[str]
    heel_counter: str
    tongue_details: str
    surface_finish: str
    visible_branding: list[str]
    toe_width: str = "not_visible"
    outsole_tread: str = "not_visible"
    seam_and_stitching_details: list[str] = []
    collar_or_opening: str = "not_visible"
    fit_and_silhouette: str = "not_visible"
    visible_uncertainties: list[str]


class DressDetails(BaseModel):
    family: DressFamily | None = None
    subtype: str
    length: str
    structure: str
    silhouette: str
    occasion: str
    fabric_appearance: str
    construction_details: list[str]
    visible_uncertainties: list[str]


class TailoringDetails(BaseModel):
    family: TailoringFamily | None = None
    subtype: str
    product_unit: str
    lapel_or_neckline: str
    closure_details: list[str]
    pocket_details: list[str]
    lining_or_structure: str
    fit_and_silhouette: str
    fabric_appearance: str
    visible_uncertainties: list[str]


class SleepwearDetails(BaseModel):
    family: SleepwearFamily | None = None
    subtype: str
    product_unit: str
    coverage: str
    closure_details: list[str]
    fit_and_silhouette: str
    fabric_appearance: str
    visible_uncertainties: list[str]


class UnifiedJewelleryDetails(BaseModel):
    family: JewelleryFamily | None = None
    subtype: str
    form: str
    closure_or_attachment: str
    material_appearance: str
    stones_or_decoration: list[str]
    surface_finish: str
    visible_uncertainties: list[str]


class AccessoriesDetails(BaseModel):
    family: AccessoriesFamily | None = None
    subtype: str
    form: str
    closure_or_adjustment: str
    material_appearance: str
    surface_finish: str
    occasion: str
    visible_uncertainties: list[str]


class ScarvesDetails(BaseModel):
    subtype: str
    scarf_shape: str
    scarf_length: str
    scarf_width: str
    edge_finish: str
    fringe_details: str
    fabric_appearance: str
    thickness: str
    pattern: str
    print: str
    drape: str
    fastening_or_wear_details: list[str]
    visible_uncertainties: list[str]


class GlovesDetails(BaseModel):
    subtype: str
    glove_type: str
    finger_configuration: str
    finger_length: str
    cuff_length: str
    cuff_details: str
    closure_details: list[str]
    palm_details: list[str]
    grip_features: list[str]
    seam_details: list[str]
    lining_or_insulation: str
    material_appearance: str
    visible_uncertainties: list[str]


class RingsDetails(BaseModel):
    subtype: str
    ring_type: str
    band_shape: str
    band_width: str
    metal_appearance: str
    stone_details: list[str]
    stone_shape: str
    stone_colour: str
    setting_details: list[str]
    surface_finish: str
    engraving_or_graphics: list[str]
    visible_uncertainties: list[str]


class WatchesDetails(BaseModel):
    subtype: str
    watch_type: str
    case_shape: str
    case_size_appearance: str
    case_material_appearance: str
    dial_colour: str
    dial_details: list[str]
    hour_markers: str
    hands: str
    sub_dials: list[str]
    bezel_details: str
    strap_or_bracelet: str
    closure_type: str
    crown_details: str
    visible_branding: list[str]
    visible_uncertainties: list[str]


class NecklacesDetails(BaseModel):
    subtype: str
    necklace_type: str
    chain_type: str
    chain_thickness: str
    necklace_length_appearance: str
    pendant_details: list[str]
    pendant_shape: str
    stone_details: list[str]
    stone_colour: str
    metal_appearance: str
    clasp_details: str
    engraving_or_graphics: list[str]
    layering_details: str
    surface_finish: str
    visible_uncertainties: list[str]


class HeadwearDetails(BaseModel):
    subtype: str
    crown_shape: str
    brim_or_peak_shape: str
    brim_width: str
    crown_height: str
    closure_or_adjustment: str
    panel_and_seam_details: list[str]
    material_appearance: str
    surface_texture: str
    surface_finish: str
    structure_or_rigidity: str
    fit_or_wear_position: str
    visible_branding: list[str]
    visible_uncertainties: list[str]


class JewelleryDetails(BaseModel):
    subtype: str
    jewellery_form: str
    shape_and_profile: str
    setting_or_structure: str
    closure_or_fastening: str
    chain_or_band_details: str
    stone_or_decoration_details: list[str]
    material_appearance: str
    surface_finish: str
    hardware_details: list[str]
    visible_branding: list[str]
    visible_uncertainties: list[str]


class NeckwearDetails(BaseModel):
    subtype: str
    shape: str
    length_and_width: str
    knot_or_fastening_details: str
    edge_finish: str
    material_appearance: str
    surface_texture: str
    pattern_or_print: str
    drape: str
    visible_branding: list[str]
    visible_uncertainties: list[str]


class BeltsDetails(BaseModel):
    subtype: str
    belt_type: str
    strap_width: str
    strap_length_appearance: str
    strap_shape: str
    material_appearance: str
    surface_texture: str
    surface_finish: str
    buckle_type: str
    buckle_shape: str
    buckle_material_appearance: str
    closure_type: str
    hole_details: str
    belt_loop_details: str
    tip_details: str
    hardware_details: list[str]
    pattern_or_print: str
    branding_or_graphics: list[str]
    fit_or_wear_position: str
    visible_uncertainties: list[str]


CategoryDetails = Union[
    TopsDetails, OuterwearDetails, BottomsDetails, UnderwearDetails,
    SocksDetails, FootwearDetails, DressDetails, TailoringDetails,
    SleepwearDetails, UnifiedJewelleryDetails, AccessoriesDetails,
    ScarvesDetails, GlovesDetails, HeadwearDetails, JewelleryDetails,
    NeckwearDetails, BeltsDetails,
]


CATEGORY_DETAIL_MODELS = {
    "tops": TopsDetails,
    "outerwear": OuterwearDetails,
    "bottoms": BottomsDetails,
    "underwear": UnderwearDetails,
    "socks": SocksDetails,
    "footwear": FootwearDetails,
    "dresses": DressDetails,
    "tailoring": TailoringDetails,
    "sleepwear_loungewear": SleepwearDetails,
    "jewellery": UnifiedJewelleryDetails,
    "accessories": AccessoriesDetails,
    "scarves": ScarvesDetails,
    "gloves": GlovesDetails,
    "headwear": HeadwearDetails,
    "rings": JewelleryDetails,
    "bracelets": JewelleryDetails,
    "earrings": JewelleryDetails,
    "neckwear": NeckwearDetails,
    "belts": BeltsDetails,
}
