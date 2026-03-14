import pytest
import os
import tarfile
from autodataset.repository.module import DatasetRepository, QueryFilters
from autodataset.models.data import RawData
from autodataset.models.specifications import DatasetSpecification, TaskType, QualityThresholds, DataSource, SourceType, DataFormat
from autodataset.models.metadata import DatasetMetadata, DatasetLineage, DatasetStatistics, QualityMetrics

@pytest.fixture
def repo(tmp_path):
    return DatasetRepository(db_url="sqlite:///:memory:", storage_dir=str(tmp_path))

def create_dummy_spec():
    return DatasetSpecification(
        spec_id="spec_123",
        domain="test",
        task_type=TaskType.CLASSIFICATION,
        target_variable="target",
        dataset_size=10,
        quality_thresholds=QualityThresholds(min_completeness=0.5, min_consistency=0.5, min_accuracy=0.5, max_anomaly_rate=0.5),
        data_sources=[DataSource(source_id="s1", source_type=SourceType.WEB, location="http://test.com", format=DataFormat.CSV)],
        created_by="tester"
    )

def create_dummy_metadata(spec):
    return DatasetMetadata(
        version_id="",
        spec=spec,
        statistics=DatasetStatistics(record_count=10, feature_count=2),
        quality_metrics=QualityMetrics(completeness=1.0, consistency=1.0, accuracy=1.0, validity=1.0, anomaly_rate=0.0),
        lineage=DatasetLineage(source_data_references=["s1"], reproducibility_hash="hash123"),
        processing_time=1.5
    )

def test_property_23_dataset_version_immutability(repo):
    """
    Feature: autodataset-platform, Property 23: Dataset Version Immutability
    """
    spec = create_dummy_spec()
    meta = create_dummy_metadata(spec)
    data = RawData(records=[{"a": 1, "b": 2}], format=DataFormat.CSV, metadata=meta)
    
    version = repo.create_version(data, spec, meta)
    
    # Try fetching it
    fetched = repo.get_version(version.version_id)
    assert fetched.version_id == version.version_id
    assert fetched.metadata.statistics.record_count == 10
    
def test_property_24_version_metadata_completeness(repo):
    """
    Feature: autodataset-platform, Property 24: Version Metadata Completeness
    """
    spec = create_dummy_spec()
    meta = create_dummy_metadata(spec)
    data = RawData(records=[{"a": 1, "b": 2}], format=DataFormat.CSV, metadata=meta)
    
    version = repo.create_version(data, spec, meta)
    fetched = repo.get_version(version.version_id)
    
    # Completeness verification
    assert fetched.spec_id == spec.spec_id
    assert fetched.metadata.quality_metrics.completeness == 1.0
    assert fetched.lineage.reproducibility_hash == "hash123"

def test_property_25_dataset_query_correctness(repo):
    """
    Feature: autodataset-platform, Property 25: Dataset Query Correctness
    """
    spec = create_dummy_spec()
    meta = create_dummy_metadata(spec)
    data = RawData(records=[{"a": 1, "b": 2}], format=DataFormat.CSV, metadata=meta)
    
    version = repo.create_version(data, spec, meta)
    
    filters = QueryFilters(spec_id="spec_123")
    results = repo.query_datasets(filters)
    assert len(results) == 1
    assert results[0].version_id == version.version_id
    
    filters2 = QueryFilters(spec_id="spec_456")
    results2 = repo.query_datasets(filters2)
    assert len(results2) == 0

def test_property_27_output_artifact_completeness(repo):
    """
    Feature: autodataset-platform, Property 27: Output Artifact Completeness
    """
    spec = create_dummy_spec()
    meta = create_dummy_metadata(spec)
    # Give it some records to write to parquet
    data = RawData(records=[{"a": 1, "b": 2}], format=DataFormat.CSV, metadata=meta)
    
    version = repo.create_version(data, spec, meta)
    
    formats = ["csv", "parquet"]
    artifacts = repo.generate_artifacts(version, formats)
    
    assert os.path.exists(artifacts.dataset_files["csv"])
    assert os.path.exists(artifacts.dataset_files["parquet"])
    assert os.path.exists(artifacts.metadata_file)
    assert os.path.exists(artifacts.schema_file)
    assert os.path.exists(artifacts.quality_report_file)
    assert os.path.exists(artifacts.archive_path)
    
    with tarfile.open(artifacts.archive_path, "r:gz") as tar:
        names = tar.getnames()
        assert any("dataset.csv" in n for n in names)
        assert any("metadata.json" in n for n in names)
