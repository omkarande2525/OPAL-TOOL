import pytest
from hypothesis import given, strategies as st
from autodataset.schema_validator.validator import SchemaValidator
from autodataset.models.data import RawData
from autodataset.models.specifications import DataFormat
from autodataset.models.metadata import DataMetadata
from autodataset.models.schemas import Schema, FieldDefinition, DataType

def test_property_5_validation_comprehensiveness():
    """
    Feature: autodataset-platform, Property 5: Schema Validation Comprehensiveness
    """
    validator = SchemaValidator()
    data = RawData(
        records=[{"id": "1", "name": "test"}],
        format=DataFormat.JSON,
        metadata=DataMetadata(record_count=1, column_count=2, size_bytes=10, source_references=["src1"], processing_history=[])
    )
    schema = Schema(
        fields=[
            FieldDefinition(name="id", data_type=DataType.INTEGER, nullable=False),
            FieldDefinition(name="name", data_type=DataType.STRING, nullable=False),
            FieldDefinition(name="age", data_type=DataType.INTEGER, nullable=False) # Missing field
        ]
    )
    result = validator.validate(data, schema)
    assert not result.is_valid
    violations = {v.field_name: v.violation_type for v in result.violations}
    assert "age" in violations
    assert violations["age"] == "MISSING_FIELD"
    
def test_property_6_schema_inference():
    """
    Feature: autodataset-platform, Property 6: Schema Inference
    """
    validator = SchemaValidator()
    data = RawData(
        records=[{"id": 1, "name": "test", "active": True, "score": 9.5}],
        format=DataFormat.JSON,
        metadata=DataMetadata(record_count=1, column_count=4, size_bytes=50, source_references=["src1"], processing_history=[])
    )
    schema = validator.infer_schema(data)
    assert len(schema.fields) == 4
    field_types = {f.name: f.data_type for f in schema.fields}
    assert field_types["id"] == DataType.INTEGER
    assert field_types["name"] == DataType.STRING
    assert field_types["active"] == DataType.BOOLEAN
    assert field_types["score"] == DataType.FLOAT

def test_property_7_multi_source_compatibility():
    """
    Feature: autodataset-platform, Property 7: Multi-Source Schema Compatibility
    """
    validator = SchemaValidator()
    s1 = Schema(fields=[FieldDefinition(name="id", data_type=DataType.INTEGER)])
    s2 = Schema(fields=[FieldDefinition(name="id", data_type=DataType.STRING)]) # Conflict
    
    result = validator.check_compatibility([s1, s2])
    assert not result.is_compatible
    assert len(result.conflicts) == 1
    
    s3 = Schema(fields=[FieldDefinition(name="name", data_type=DataType.STRING)]) # Compatible
    result2 = validator.check_compatibility([s1, s3])
    assert result2.is_compatible
