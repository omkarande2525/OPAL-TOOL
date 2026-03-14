import pandas as pd
from typing import List, Optional, Dict
from pydantic import BaseModel
from autodataset.models.schemas import Schema, FieldDefinition, DataType, SchemaConstraint, FieldConstraint
from autodataset.models.data import RawData

class SchemaViolation(BaseModel):
    field_name: str
    violation_type: str
    description: str

class ValidationResult(BaseModel):
    is_valid: bool
    violations: List[SchemaViolation]
    inferred_schema: Optional[Schema]

class CompatibilityResult(BaseModel):
    is_compatible: bool
    merged_schema: Optional[Schema]
    conflicts: List[str]

class SchemaValidator:
    def validate(self, data: RawData, expected_schema: Optional[Schema]) -> ValidationResult:
        if not expected_schema:
            inferred = self.infer_schema(data)
            return ValidationResult(is_valid=True, violations=[], inferred_schema=inferred)
        
        violations = []
        if not data.records:
            return ValidationResult(is_valid=True, violations=[], inferred_schema=None)
            
        df = pd.DataFrame(data.records)
        for field in expected_schema.fields:
            if field.name not in df.columns:
                if not field.nullable:
                    violations.append(SchemaViolation(
                        field_name=field.name,
                        violation_type="MISSING_FIELD",
                        description=f"Required field '{field.name}' is missing"
                    ))
                continue
            
            actual_dtype = df[field.name].dtype
            if field.data_type == DataType.INTEGER and not pd.api.types.is_integer_dtype(actual_dtype):
                violations.append(SchemaViolation(
                    field_name=field.name,
                    violation_type="TYPE_MISMATCH",
                    description=f"Expected INTEGER but got {actual_dtype}"
                ))
            elif field.data_type == DataType.FLOAT and not pd.api.types.is_numeric_dtype(actual_dtype):
                violations.append(SchemaViolation(
                    field_name=field.name,
                    violation_type="TYPE_MISMATCH",
                    description=f"Expected FLOAT but got {actual_dtype}"
                ))
            elif field.data_type == DataType.BOOLEAN and not pd.api.types.is_bool_dtype(actual_dtype):
                violations.append(SchemaViolation(
                    field_name=field.name,
                    violation_type="TYPE_MISMATCH",
                    description=f"Expected BOOLEAN but got {actual_dtype}"
                ))
                
        is_valid = len(violations) == 0
        return ValidationResult(is_valid=is_valid, violations=violations, inferred_schema=None)

    def infer_schema(self, data: RawData) -> Schema:
        if not data.records:
            return Schema(fields=[], constraints=[])
            
        df = pd.DataFrame(data.records)
        fields = []
        for col in df.columns:
            dtype = df[col].dtype
            if pd.api.types.is_integer_dtype(dtype):
                data_type = DataType.INTEGER
            elif pd.api.types.is_float_dtype(dtype):
                data_type = DataType.FLOAT
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                data_type = DataType.DATETIME
            elif pd.api.types.is_bool_dtype(dtype):
                data_type = DataType.BOOLEAN
            else:
                data_type = DataType.STRING
                
            nullable = bool(df[col].isnull().any())
            fields.append(FieldDefinition(name=col, data_type=data_type, nullable=nullable))
            
        return Schema(fields=fields, constraints=[])

    def check_compatibility(self, schemas: List[Schema]) -> CompatibilityResult:
        if not schemas:
            return CompatibilityResult(is_compatible=True, merged_schema=None, conflicts=[])
            
        base_schema = schemas[0]
        conflicts = []
        
        field_map = {f.name: f for f in base_schema.fields}
        
        for s in schemas[1:]:
            for field in s.fields:
                if field.name in field_map:
                    if field.data_type != field_map[field.name].data_type:
                        conflicts.append(f"Type conflict for {field.name}: {field.data_type} vs {field_map[field.name].data_type}")
                else:
                    field_map[field.name] = field
                    
        is_compatible = len(conflicts) == 0
        merged = Schema(fields=list(field_map.values()), constraints=[]) if is_compatible else None
        return CompatibilityResult(is_compatible=is_compatible, merged_schema=merged, conflicts=conflicts)
