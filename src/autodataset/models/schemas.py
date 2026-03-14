from enum import Enum
from typing import List, Optional, Any
from pydantic import BaseModel

class DataType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    CATEGORICAL = "categorical"

class FieldConstraint(BaseModel):
    constraint_type: str
    value: Any

class FieldDefinition(BaseModel):
    name: str
    data_type: DataType
    nullable: bool = True
    constraints: Optional[List[FieldConstraint]] = []

class SchemaConstraint(BaseModel):
    constraint_type: str
    fields: List[str]

class Schema(BaseModel):
    fields: List[FieldDefinition]
    constraints: Optional[List[SchemaConstraint]] = []
