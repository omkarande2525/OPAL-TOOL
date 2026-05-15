from typing import Dict, List, Any, Optional
from pydantic import BaseModel, ConfigDict
from .schemas import Schema, DataMetadata
from .specifications import DataFormat

class RawData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    records: List[Dict[str, Any]]
    schema_def: Optional[Schema] = None
    metadata: DataMetadata
    format: DataFormat
