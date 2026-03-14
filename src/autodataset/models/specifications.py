from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, model_validator

class TaskType(str, Enum):
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    CLUSTERING = "clustering"
    TIME_SERIES = "time_series"

class SourceType(str, Enum):
    WEB = "web"
    API = "api"
    PUBLIC_DATASET = "public_dataset"

class DataFormat(str, Enum):
    CSV = "csv"
    JSON = "json"
    XML = "xml"
    PARQUET = "parquet"

class AuthConfig(BaseModel):
    auth_type: str
    credentials: Dict[str, str]

class DataSource(BaseModel):
    source_id: str
    source_type: SourceType
    location: str
    auth_config: Optional[AuthConfig] = None
    format: DataFormat

class FeatureRule(BaseModel):
    feature_name: str
    rule_type: str
    parameters: Dict[str, Any]

class ScalingConfig(BaseModel):
    method: str

class EncodingMethod(str, Enum):
    ONE_HOT = "one_hot"
    LABEL = "label"
    TARGET = "target"

class TransformationConfig(BaseModel):
    encoding_method: Optional[EncodingMethod] = None
    feature_rules: Optional[List[FeatureRule]] = None
    scaling_config: Optional[ScalingConfig] = None

class FeatureConfig(BaseModel):
    transformation_config: Optional[TransformationConfig] = None

class QualityThresholds(BaseModel):
    min_completeness: float = Field(ge=0.0, le=1.0)
    min_consistency: float = Field(ge=0.0, le=1.0)
    min_accuracy: float = Field(ge=0.0, le=1.0)
    max_anomaly_rate: float = Field(ge=0.0, le=1.0)

class DatasetSpecification(BaseModel):
    spec_id: str
    domain: str
    task_type: TaskType
    target_variable: str
    dataset_size: int = Field(gt=0)
    class_balance_constraints: Optional[Dict[str, float]] = None
    quality_thresholds: QualityThresholds
    data_sources: List[DataSource] = Field(min_length=1)
    feature_config: Optional[FeatureConfig] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str

    @model_validator(mode='after')
    def validate_class_balance(self) -> 'DatasetSpecification':
        if self.class_balance_constraints is not None:
            total = sum(self.class_balance_constraints.values())
            # Float precision comparison
            if not (0.999 <= total <= 1.001):
                raise ValueError("Class balance constraints must sum to 1.0")
        return self
