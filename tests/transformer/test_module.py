import pytest
import pandas as pd
from autodataset.transformer.module import DataTransformer
from autodataset.models.specifications import TransformationConfig, EncodingMethod, FeatureRule, DataFormat
from autodataset.models.data import RawData
from autodataset.models.metadata import DataMetadata

def get_base_metadata():
    return DataMetadata(record_count=0, column_count=0, size_bytes=0, source_references=[], processing_history=[])

def test_property_13_categorical_encoding():
    """
    Feature: autodataset-platform, Property 13: Categorical Encoding Consistency
    """
    data = RawData(
        records=[{"val": 10, "cat": "A"}, {"val": 20, "cat": "B"}],
        format=DataFormat.JSON,
        metadata=get_base_metadata()
    )
    config = TransformationConfig(encoding_method=EncodingMethod.ONE_HOT)
    transformer = DataTransformer()
    result = transformer.transform(data, config)
    rec = result.transformed_data.records[0]
    # Check if 'cat_A' or similar one-hot column exists
    assert any(k.startswith("cat_") for k in rec.keys())

def test_property_14_custom_transformation():
    """
    Feature: autodataset-platform, Property 14: Custom Transformation Application
    """
    data = RawData(
        records=[{"val": 10}, {"val": 20}],
        format=DataFormat.JSON,
        metadata=get_base_metadata()
    )
    transformer = DataTransformer()
    def custom_func(df: pd.DataFrame) -> pd.DataFrame:
        df["val_double"] = df["val"] * 2
        return df
        
    result = transformer.apply_custom_transformation(data, custom_func)
    assert result.transformed_data.records[0]["val_double"] == 20
    assert result.transformed_data.records[1]["val_double"] == 40
    assert len(result.transformation_log) == 1

def test_property_15_transformation_reproducibility():
    """
    Feature: autodataset-platform, Property 15: Transformation Reproducibility
    """
    data = RawData(
        records=[{"val": 10, "cat": "A"}, {"val": 20, "cat": "B"}],
        format=DataFormat.JSON,
        metadata=get_base_metadata()
    )
    config = TransformationConfig(
        encoding_method=EncodingMethod.LABEL,
        feature_rules=[FeatureRule(feature_name="val", rule_type="polynomial", parameters={"degree": 2})]
    )
    transformer = DataTransformer()
    result = transformer.transform(data, config)
    
    # Log must contain the steps
    types = [l.transformation_type for l in result.transformation_log]
    assert "encoding" in types
    assert "polynomial" in types
    assert result.transformed_data.records[0]["val_poly_2"] == 100
