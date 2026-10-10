"""Pydantic models. Every sourced value carries an origin tag; missing values are None, never 0."""
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

# qloo_live | merchant_input | public_external | historical_data | synthetic | model_estimate
Origin = str


class SKU(BaseModel):
    id: str
    name: str
    price: float
    unit_cost: float
    salvage_value: float
    moq: int
    lot_size: int
    max_stock: int
    base_weight: float = 1.0
    concept_tags: List[str]
    requires_license: Optional[str] = None
    rain_factor: float = 1.0  # demand multiplier under rain (model_estimate)
    shelf_life_days: Optional[int] = None


class RecipeLine(BaseModel):
    ingredient: str
    unit: str
    qty_per_unit: float
    waste_rate: float


class Capacity(BaseModel):
    units_per_hour: float
    hours: int
    hourly_profile: List[float]
    label: str


class Merchant(BaseModel):
    id: str
    name: str
    segment: str
    currency: str
    budget: float
    licenses_held: List[str]
    booth_reach: float
    conversion: float
    units_per_buyer: float
    skus: List[SKU]
    capacity: Optional[Capacity] = None
    recipes: Dict[str, List[RecipeLine]] = Field(default_factory=dict)


class Event(BaseModel):
    id: str
    name: str
    theme: str
    geo: str
    date: str
    attendance: int
    attendance_source: Origin
    seed_concepts: List[str]
    days: int = 1
    day_curve: List[float] = Field(default_factory=list)


class QlooEvidence(BaseModel):
    id: str
    tag_id: str
    tag: str
    affinity: Optional[float]  # None = unknown
    origin: Origin
    query_id: str
    note: Optional[str] = None


class Scenario(BaseModel):
    """What-if levers. All multipliers default to no change."""
    rain: bool = False
    attendance_factor: float = 1.0
    cost_factor: float = 1.0
    price_factor: float = 1.0
    competitor_factor: float = 1.0  # share of booth traffic kept when rival stalls appear
    moq_factor: float = 1.0


class PlanRequest(BaseModel):
    event_id: str
    merchant_id: str = "merchant_souvenir_01"
    attendance: Optional[int] = None
    budget: Optional[float] = None
    qloo_on: bool = True
    seed: int = 42
    risk: str = "balanced"  # conservative | balanced | aggressive
    scenario: Optional[Scenario] = None
    weight_overrides: Dict[str, float] = Field(default_factory=dict)  # from post-event calibration


class AblationRequest(BaseModel):
    event_id: str
    merchant_id: str = "merchant_souvenir_01"
    attendance: Optional[int] = None
    budget: Optional[float] = None
    seed: int = 42


class SkuPlan(BaseModel):
    sku_id: str
    name: str
    affinity: Optional[float]
    affinity_status: str  # known | partial | unknown | not_used
    evidence_ids: List[str]
    demand_p10: float
    demand_p50: float
    demand_p90: float
    stock_qty: int
    cost: float
    expected_profit: float
    stockout_risk: Optional[float]
    leftover_units: float
    excluded_reason: Optional[str] = None


class IngredientNeed(BaseModel):
    ingredient: str
    unit: str
    quantity: float
    for_skus: List[str]


class Plan(BaseModel):
    decision_id: str
    event_id: str
    merchant_id: str = ""
    risk: str = "balanced"
    scenario_notes: List[str] = Field(default_factory=list)
    ingredients: List[IngredientNeed] = Field(default_factory=list)
    capacity_note: Optional[str] = None
    metrics: Dict[str, Optional[float]] = Field(default_factory=dict)
    qloo_on: bool
    qloo_mode: str  # live | mock
    attendance: int
    budget: float
    total_cost: float
    expected_profit: float
    skus: List[SkuPlan]
    event_dna: List[QlooEvidence]
    assumptions: Dict[str, float] = Field(default_factory=dict)
