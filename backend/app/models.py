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


class Event(BaseModel):
    id: str
    name: str
    theme: str
    geo: str
    date: str
    attendance: int
    attendance_source: Origin
    seed_concepts: List[str]


class QlooEvidence(BaseModel):
    id: str
    tag_id: str
    tag: str
    affinity: Optional[float]  # None = unknown
    origin: Origin
    query_id: str
    note: Optional[str] = None


class PlanRequest(BaseModel):
    event_id: str
    attendance: Optional[int] = None
    budget: Optional[float] = None
    qloo_on: bool = True
    seed: int = 42


class AblationRequest(BaseModel):
    event_id: str
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


class Plan(BaseModel):
    decision_id: str
    event_id: str
    qloo_on: bool
    qloo_mode: str  # live | mock
    attendance: int
    budget: float
    total_cost: float
    expected_profit: float
    skus: List[SkuPlan]
    event_dna: List[QlooEvidence]
    assumptions: Dict[str, float] = Field(default_factory=dict)
