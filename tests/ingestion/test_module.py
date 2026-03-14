import pytest
import os
import json
from unittest.mock import patch, MagicMock
from hypothesis import given, strategies as st

from autodataset.ingestion.module import DataIngestionModule, SourceError
from autodataset.models.specifications import DataSource, SourceType, DataFormat
from autodataset.models.data import RawData
from autodataset.models.metadata import DataMetadata

@pytest.fixture
def mock_dir(tmp_path):
    return str(tmp_path)

def test_property_3_ingestion_resilience(mock_dir):
    """
    Feature: autodataset-platform, Property 3: Data Ingestion Resilience
    """
    module = DataIngestionModule(raw_data_dir=mock_dir)
    
    valid_source = DataSource(
        source_id="src_valid", source_type=SourceType.WEB, location="http://example.com/valid", format=DataFormat.CSV
    )
    invalid_source = DataSource(
        source_id="src_invalid", source_type=SourceType.WEB, location="http://example.com/invalid", format=DataFormat.CSV
    )
    
    with patch.object(module, 'fetch_from_web') as mock_fetch:
        def side_effect(source):
            if source.source_id == "src_valid":
                return RawData(
                    records=[{"a": 1}],
                    metadata=DataMetadata(record_count=1, column_count=1, size_bytes=10, source_references=["src_valid"], processing_history=[]),
                    format=DataFormat.CSV
                )
            else:
                raise Exception("Failed to fetch")
        mock_fetch.side_effect = side_effect
        
        result = module.ingest([valid_source, invalid_source])
        
        assert len(result.successful_sources) == 1
        assert "src_valid" in result.successful_sources
        assert len(result.failed_sources) == 1
        assert result.failed_sources[0].source_id == "src_invalid"
        assert len(result.raw_data) == 1

def test_property_4_raw_data_preservation(mock_dir):
    """
    Feature: autodataset-platform, Property 4: Raw Data Preservation
    """
    module = DataIngestionModule(raw_data_dir=mock_dir)
    valid_source = DataSource(
        source_id="src_preserve", source_type=SourceType.WEB, location="http://example.com/valid", format=DataFormat.CSV
    )
    
    with patch.object(module, 'fetch_from_web') as mock_fetch:
        mock_fetch.return_value = RawData(
            records=[{"key": "value"}],
            metadata=DataMetadata(record_count=1, column_count=1, size_bytes=15, source_references=["src_preserve"], processing_history=[]),
            format=DataFormat.CSV
        )
        module.ingest([valid_source])
        
        # Check if preserved
        preserved_file = os.path.join(mock_dir, "src_preserve_raw.json")
        assert os.path.exists(preserved_file)
        with open(preserved_file, 'r') as f:
            data = json.load(f)
            assert data == [{"key": "value"}]

def test_format_parsing():
    content = b"a,b\n1,2"
    module = DataIngestionModule(raw_data_dir="/tmp")
    data = module._parse_response(content, DataFormat.CSV, "src_csv")
    assert len(data.records) == 1
    assert data.records[0] == {"a": 1, "b": 2}

    json_content = b'[{"a": 1, "b": 2}]'
    data_json = module._parse_response(json_content, DataFormat.JSON, "src_json")
    assert len(data_json.records) == 1
    assert data_json.records[0] == {"a": 1, "b": 2}
