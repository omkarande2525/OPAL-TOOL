import pytest
from autodataset.cleaner.module import DataCleaner, CleaningConfig, MissingValueStrategy, NormalizationConfig, NormalizationMethod, OutlierConfig, OutlierMethod
from autodataset.models.data import RawData
from autodataset.models.specifications import DataFormat
from autodataset.models.metadata import DataMetadata

@pytest.fixture
def mock_cleaner():
    return DataCleaner()

def get_base_metadata():
    return DataMetadata(record_count=0, column_count=0, size_bytes=0, source_references=[], processing_history=[])

def test_property_8_duplicate_removal(mock_cleaner):
    """
    Feature: autodataset-platform, Property 8: Duplicate Record Removal
    """
    data = RawData(
        records=[{"id": 1, "val": "A"}, {"id": 1, "val": "A"}, {"id": 2, "val": "B"}],
        format=DataFormat.JSON,
        metadata=get_base_metadata()
    )
    config = CleaningConfig(remove_duplicates=True)
    result = mock_cleaner.clean(data, config)
    assert len(result.cleaned_data.records) == 2
    assert result.cleaning_report.duplicates_removed == 1

def test_property_9_missing_value_handling(mock_cleaner):
    """
    Feature: autodataset-platform, Property 9: Missing Value Handling
    """
    data = RawData(
        records=[{"val": 10}, {"val": None}, {"val": 30}],
        format=DataFormat.JSON,
        metadata=get_base_metadata()
    )
    config = CleaningConfig(missing_value_strategy=MissingValueStrategy.IMPUTE_MEAN)
    result = mock_cleaner.clean(data, config)
    # The missing value should be 20.0
    assert len(result.cleaned_data.records) == 3
    assert result.cleaned_data.records[1]["val"] == 20.0

def test_property_10_numerical_normalization(mock_cleaner):
    """
    Feature: autodataset-platform, Property 10: Numerical Feature Normalization
    """
    data = RawData(
        records=[{"val": 0}, {"val": 50}, {"val": 100}],
        format=DataFormat.JSON,
        metadata=get_base_metadata()
    )
    config = CleaningConfig(
        normalization_config=NormalizationConfig(features=["val"], method=NormalizationMethod.MIN_MAX)
    )
    result = mock_cleaner.clean(data, config)
    assert result.cleaned_data.records[0]["val"] == 0.0
    assert result.cleaned_data.records[1]["val"] == 0.5
    assert result.cleaned_data.records[2]["val"] == 1.0

def test_property_11_outlier_detection(mock_cleaner):
    """
    Feature: autodataset-platform, Property 11: Outlier Detection and Handling
    """
    # 0, 1, 2, 3 are normal, 1000 is outlier
    data = RawData(
        records=[{"val": 0}, {"val": 1}, {"val": 2}, {"val": 3}, {"val": 100}],
        format=DataFormat.JSON,
        metadata=get_base_metadata()
    )
    config = CleaningConfig(
        outlier_config=OutlierConfig(features=["val"], method=OutlierMethod.Z_SCORE, threshold=1.5)
    )
    result = mock_cleaner.clean(data, config)
    # 100 has a huge Z-score and should be removed
    assert len(result.cleaned_data.records) < 5
    assert result.cleaning_report.outliers_handled > 0

def test_property_12_cleaning_reporting(mock_cleaner):
    """
    Feature: autodataset-platform, Property 12: Cleaning Operation Reporting
    """
    data = RawData(
        records=[{"val": 0}, {"val": 0}, {"val": None}],
        format=DataFormat.JSON,
        metadata=get_base_metadata()
    )
    config = CleaningConfig(remove_duplicates=True, missing_value_strategy=MissingValueStrategy.IMPUTE_MEAN)
    result = mock_cleaner.clean(data, config)
    report = result.cleaning_report
    assert report.records_before == 3
    assert report.duplicates_removed == 1
    assert len(report.actions) > 0
    action_types = [a.action for a in report.actions]
    assert "remove_duplicates" in action_types
    assert "handle_missing" in action_types
