import pytest
import pandas as pd
from autodataset.models.data import RawData
from autodataset.models.specifications import DataFormat, QualityThresholds
from autodataset.models.metadata import DataMetadata
from autodataset.quality.module import QualityAnalyzer, AnomalyDetector

def get_base_metadata():
    return DataMetadata(record_count=0, column_count=0, size_bytes=0, source_references=[], processing_history=[])

def test_property_20_quality_metrics_computation():
    """
    Feature: autodataset-platform, Property 20: Quality Metrics Computation
    """
    analyzer = QualityAnalyzer()
    data = RawData(
        # 10 cells total, 2 missing values -> 80% completeness
        records=[
            {"id": 1, "val": 10},
            {"id": 2, "val": 20},
            {"id": 3, "val": None},
            {"id": 4, "val": 40},
            {"id": None, "val": 50}
        ],
        format=DataFormat.CSV,
        metadata=get_base_metadata()
    )
    thresholds = QualityThresholds(
        min_completeness=0.5,
        min_consistency=0.5,
        min_accuracy=0.5,
        max_anomaly_rate=0.5
    )
    result = analyzer.analyze(data, thresholds)
    
    # 2 nulls out of 10 values = 0.8 completeness
    assert result.metrics["completeness"] == 0.8
    assert result.quality_report.completeness == 0.8
    
    assert result.metrics["consistency"] == 1.0
    assert result.metrics["accuracy"] == 1.0

def test_property_21_quality_threshold_enforcement():
    """
    Feature: autodataset-platform, Property 21: Quality Threshold Enforcement
    """
    analyzer = QualityAnalyzer()
    data = RawData(
        records=[
            {"id": 1, "val": 10},
            {"id": 2, "val": None},
            {"id": 3, "val": None},
            {"id": 4, "val": 40}
        ], # 2 nulls out of 8 cells = 0.75 completeness
        format=DataFormat.CSV,
        metadata=get_base_metadata()
    )
    thresholds = QualityThresholds(
        min_completeness=0.9, # should fail
        min_consistency=0.5,
        min_accuracy=0.5,
        max_anomaly_rate=0.5
    )
    result = analyzer.analyze(data, thresholds)
    
    assert not result.passes_thresholds
    assert not result.quality_report.pass_all_thresholds
    assert any("completeness" in m for m in result.quality_report.failing_metrics)

def test_property_22_anomaly_detection_and_reporting():
    """
    Feature: autodataset-platform, Property 22: Anomaly Detection and Reporting
    """
    analyzer = QualityAnalyzer()
    data = RawData(
        # 0, 1, 2, 3 -> low variance. 1000 is high z-score
        records=[{"val": i} for i in range(10)] + [{"val": 1000}],
        format=DataFormat.CSV,
        metadata=get_base_metadata()
    )
    thresholds = QualityThresholds(
        min_completeness=0.0,
        min_consistency=0.0,
        min_accuracy=0.0,
        max_anomaly_rate=1.0 # won't fail thresholds
    )
    result = analyzer.analyze(data, thresholds)
    
    assert result.anomalies.total_anomalies > 0
    assert len(result.anomalies.anomalies) > 0
    anomaly = result.anomalies.anomalies[0]
    
    # Severity should be assigned
    assert anomaly.severity in ["low", "medium", "high"]
    assert 10 in anomaly.indices # The last element is index 10
