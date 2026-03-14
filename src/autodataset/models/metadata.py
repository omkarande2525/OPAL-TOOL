from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
from .specifications import DatasetSpecification
from .schemas import Schema

class ProcessingStep(BaseModel):
    stage: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    parameters: Dict[str, Any] = {}
    metrics: Dict[str, Any] = {}

class FeatureStats(BaseModel):
    missing_count: int
    unique_count: int
    mean: Optional[float] = None
    std: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    value_counts: Optional[Dict[str, int]] = None

class DatasetStatistics(BaseModel):
    record_count: int
    feature_count: int
    class_distribution: Optional[Dict[str, int]] = None
    feature_statistics: Dict[str, FeatureStats] = {}
    missing_value_counts: Dict[str, int] = {}

class DatasetLineage(BaseModel):
    source_data_references: List[str]
    pipeline_stages: List[ProcessingStep] = []
    transformation_log: List[str] = []
    reproducibility_hash: str

class QualityMetrics(BaseModel):
    completeness: float
    consistency: float
    accuracy: float
    validity: float
    anomaly_rate: float

class DatasetMetadata(BaseModel):
    version_id: str
    spec: DatasetSpecification
    statistics: DatasetStatistics
    quality_metrics: QualityMetrics
    lineage: DatasetLineage
    processing_time: float
    artifact_locations: Dict[str, str] = {}
