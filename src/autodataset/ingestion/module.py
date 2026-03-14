import io
import json
import os
import pandas as pd
import requests
import structlog
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from autodataset.models.specifications import DataSource, SourceType, DataFormat
from autodataset.models.data import RawData
from autodataset.models.metadata import DataMetadata

logger = structlog.get_logger()

class SourceError(BaseModel):
    source_id: str
    error_message: str

class IngestionMetadata(BaseModel):
    total_records: int
    start_time: datetime
    end_time: datetime

class IngestionResult(BaseModel):
    raw_data: List[RawData]
    successful_sources: List[str]
    failed_sources: List[SourceError]
    ingestion_metadata: IngestionMetadata

class DataIngestionModule:
    def __init__(self, raw_data_dir: str = "/tmp/raw_data"):
        self.raw_data_dir = raw_data_dir

    def ingest(self, sources: List[DataSource]) -> IngestionResult:
        logger.info("Starting ingestion", source_count=len(sources))
        start_time = datetime.utcnow()
        raw_data_list = []
        successful_sources = []
        failed_sources = []
        
        for source in sources:
            try:
                if source.source_type == SourceType.WEB:
                    data = self.fetch_from_web(source)
                elif source.source_type == SourceType.API:
                    data = self.fetch_from_api(source)
                elif source.source_type == SourceType.PUBLIC_DATASET:
                    data = self.fetch_from_public_dataset(source)
                else:
                    raise ValueError(f"Unknown source type: {source.source_type}")
                
                raw_data_list.append(data)
                successful_sources.append(source.source_id)
                self._preserve_raw_data(data, source.source_id)
            except Exception as e:
                logger.error("Source ingestion failed", source_id=source.source_id, error=str(e))
                failed_sources.append(SourceError(source_id=source.source_id, error_message=str(e)))
        
        total_records = sum(len(rd.records) for rd in raw_data_list)
        return IngestionResult(
            raw_data=raw_data_list,
            successful_sources=successful_sources,
            failed_sources=failed_sources,
            ingestion_metadata=IngestionMetadata(
                total_records=total_records,
                start_time=start_time,
                end_time=datetime.utcnow()
            )
        )

    def _preserve_raw_data(self, data: RawData, source_id: str):
        # Implementation for raw data preservation to a separate durable location
        os.makedirs(self.raw_data_dir, exist_ok=True)
        path = os.path.join(self.raw_data_dir, f"{source_id}_raw.json")
        with open(path, 'w') as f:
            f.write(json.dumps([r for r in data.records], default=str))
        logger.info("Preserved raw data", source_id=source_id, path=path)

    def fetch_from_web(self, source: DataSource) -> RawData:
        logger.info("Fetching from web", url=source.location)
        response = requests.get(source.location, timeout=10)
        response.raise_for_status()
        return self._parse_response(response.content, source.format, source.source_id)

    def fetch_from_api(self, source: DataSource) -> RawData:
        logger.info("Fetching from API", url=source.location)
        headers = {}
        if source.auth_config:
            if source.auth_config.auth_type.lower() == "bearer":
                headers["Authorization"] = f"Bearer {source.auth_config.credentials.get('token')}"
        response = requests.get(source.location, headers=headers, timeout=10)
        response.raise_for_status()
        return self._parse_response(response.content, source.format, source.source_id)

    def fetch_from_public_dataset(self, source: DataSource) -> RawData:
        logger.info("Fetching from public dataset", id=source.location)
        # Mock logic to represent public dataset fetching
        return self.fetch_from_web(source)

    def _parse_response(self, content: bytes, format: DataFormat, source_id: str) -> RawData:
        if format == DataFormat.CSV:
            df = pd.read_csv(io.BytesIO(content))
        elif format == DataFormat.JSON:
            df = pd.read_json(io.BytesIO(content))
        elif format == DataFormat.PARQUET:
            df = pd.read_parquet(io.BytesIO(content))
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        records = df.to_dict(orient="records")
        metadata = DataMetadata(
            record_count=len(records),
            column_count=len(df.columns),
            size_bytes=len(content),
            source_references=[source_id],
            processing_history=[]
        )
        return RawData(
            records=records,
            metadata=metadata,
            format=format
        )
