import pytest
import pandas as pd
from autodataset.models.data import RawData
from autodataset.models.specifications import DataFormat
from autodataset.models.metadata import DataMetadata
from autodataset.balancer.module import ClassBalancer

def get_base_metadata():
    return DataMetadata(record_count=0, column_count=0, size_bytes=0, source_references=[], processing_history=[])

def test_property_18_class_distribution_balancing():
    """
    Feature: autodataset-platform, Property 18: Class Distribution Balancing
    """
    balancer = ClassBalancer()
    data = RawData(
        # Highly imbalanced: A=4, B=1
        records=[
            {"target": "A", "val": 1},
            {"target": "A", "val": 2},
            {"target": "A", "val": 3},
            {"target": "A", "val": 4},
            {"target": "B", "val": 5}
        ],
        format=DataFormat.CSV,
        metadata=get_base_metadata()
    )
    
    # We want A=0.5, B=0.5 with target size=10
    constraints = {"A": 0.5, "B": 0.5}
    target_size = 10
    
    result = balancer.balance(data, "target", constraints, target_size, "random")
    
    assert result.final_distribution["A"] == 5
    assert result.final_distribution["B"] == 5
    assert len(result.balanced_data.records) == 10

def test_property_19_balancing_reporting():
    """
    Feature: autodataset-platform, Property 19: Class Balancing Reporting
    """
    balancer = ClassBalancer()
    data = RawData(
        records=[{"target": "A"}, {"target": "B"}, {"target": "B"}],
        format=DataFormat.CSV,
        metadata=get_base_metadata()
    )
    
    constraints = {"A": 0.7, "B": 0.3}
    target_size = 10
    
    result = balancer.balance(data, "target", constraints, target_size, "random")
    report = result.balancing_report
    
    assert report.original_distribution["A"] == 1
    assert report.original_distribution["B"] == 2
    
    assert report.target_distribution["A"] == 7
    assert report.target_distribution["B"] == 3
    
    assert report.final_distribution["A"] == 7
    assert report.final_distribution["B"] == 3
    
    assert report.strategy_used == "random"
