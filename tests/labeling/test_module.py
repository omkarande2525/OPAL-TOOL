import pytest
import pandas as pd
from autodataset.models.data import RawData
from autodataset.models.specifications import DataFormat
from autodataset.models.metadata import DataMetadata
from autodataset.labeling.module import LabelingEngine, LabelingConfig, LabelingRule

def get_base_metadata():
    return DataMetadata(record_count=0, column_count=0, size_bytes=0, source_references=[], processing_history=[])

def test_property_16_rule_based_labeling():
    """
    Feature: autodataset-platform, Property 16: Rule-Based Labeling Application
    """
    engine = LabelingEngine()
    data = RawData(
        records=[{"val": 10}, {"val": 50}],
        format=DataFormat.JSON,
        metadata=get_base_metadata()
    )
    config = LabelingConfig(
        labeling_rules=[LabelingRule(rule_name="thresh_rule", description="Val > 20 is positive")],
        target_variable="target",
        confidence_threshold=0.8
    )
    
    def thresh_rule(row: pd.Series):
        if row["val"] > 20:
            return ("POSITIVE", 0.9)
        return ("NEGATIVE", 0.9)
        
    result = engine.label(data, config, {"thresh_rule": thresh_rule})
    
    assert result.labeled_data.records[0]["target"] == "NEGATIVE"
    assert result.labeled_data.records[1]["target"] == "POSITIVE"

def test_property_17_labeling_confidence():
    """
    Feature: autodataset-platform, Property 17: Labeling Confidence Tracking
    """
    engine = LabelingEngine()
    data = RawData(
        records=[{"val": 10}, {"val": 30}],
        format=DataFormat.JSON,
        metadata=get_base_metadata()
    )
    config = LabelingConfig(
        labeling_rules=[LabelingRule(rule_name="rule1", description="desc")],
        target_variable="target",
        confidence_threshold=0.8
    )
    
    def rule1(row: pd.Series):
        if row["val"] == 10:
            # Low confidence
            return ("A", 0.5)
        # High confidence
        return ("B", 0.9)
        
    result = engine.label(data, config, {"rule1": rule1})
    
    # Val 10 should not be labeled because confidence 0.5 < 0.8
    assert pd.isna(result.labeled_data.records[0]["target"])
    assert result.labeled_data.records[1]["target"] == "B"
    
    rep = result.labeling_report
    assert rep.labeled_records == 1
    assert rep.success_percentage == 50.0
    assert result.confidence_scores[0] == 0.5
    assert result.confidence_scores[1] == 0.9

def test_validate_labels():
    engine = LabelingEngine()
    data = RawData(
        records=[{"target": "A"}, {"target": "B"}, {"target": "C"}],
        format=DataFormat.JSON,
        metadata=get_base_metadata()
    )
    assert engine.validate_labels(data, "target", ["A", "B", "C"])
    assert not engine.validate_labels(data, "target", ["A", "B"])
