"""Category-specific visual schemas used by product recognition."""
from typing import Union

from pydantic import BaseModel, Field


class TopsDetails(BaseModel):
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


class BottomsDetails(BaseModel):
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


class UnderwearDetails(BaseModel):
    subtype: str
    coverage: str
    waist_height: str
    rise: str
    strap_type: str
    strap_width: str
    support_details: str
    cup_shape: str
    elastic_details: str
    closure_details: list[str]
    seam_details: list[str]
    fabric_appearance: str
    fit_and_silhouette: str
    visible_uncertainties: list[str]


class SocksDetails(BaseModel):
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
    SocksDetails, FootwearDetails, ScarvesDetails, GlovesDetails,
    HeadwearDetails, JewelleryDetails, NeckwearDetails, BeltsDetails,
]


CATEGORY_DETAIL_MODELS = {
    "tops": TopsDetails,
    "outerwear": OuterwearDetails,
    "bottoms": BottomsDetails,
    "underwear": UnderwearDetails,
    "socks": SocksDetails,
    "footwear": FootwearDetails,
    "scarves": ScarvesDetails,
    "gloves": GlovesDetails,
    "headwear": HeadwearDetails,
    "rings": JewelleryDetails,
    "bracelets": JewelleryDetails,
    "earrings": JewelleryDetails,
    "neckwear": NeckwearDetails,
    "belts": BeltsDetails,
}
