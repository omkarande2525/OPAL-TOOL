import os
import json
import uuid
import shutil
import tarfile
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel

from autodataset.models.data import RawData
from autodataset.models.specifications import DatasetSpecification
from autodataset.models.metadata import DatasetMetadata, DatasetLineage
from autodataset.repository.models import Base, DatasetVersionModel

class QueryFilters(BaseModel):
    spec_id: Optional[str] = None
    created_after: Optional[datetime] = None

class OutputArtifacts(BaseModel):
    dataset_files: Dict[str, str]
    metadata_file: str
    schema_file: str
    quality_report_file: str
    archive_path: Optional[str]

class DatasetVersion(BaseModel):
    version_id: str
    spec_id: str
    data_location: str
    metadata: DatasetMetadata
    lineage: DatasetLineage
    created_at: datetime

class DatasetRepository:
    def __init__(self, db_url: str = "sqlite:///:memory:", storage_dir: str = "/tmp/datasets"):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        
    def create_version(self, data: RawData, spec: DatasetSpecification, metadata: DatasetMetadata) -> DatasetVersion:
        version_id = f"v_{uuid.uuid4().hex[:8]}"
        metadata.version_id = version_id
        
        # Save data to storage
        location = os.path.join(self.storage_dir, version_id)
        os.makedirs(location, exist_ok=True)
        
        data_path = os.path.join(location, "data.json")
        with open(data_path, "w") as f:
            json.dump(data.records, f, default=str)
            
        version = DatasetVersion(
            version_id=version_id,
            spec_id=spec.spec_id,
            data_location=location,
            metadata=metadata,
            lineage=metadata.lineage,
            created_at=datetime.utcnow()
        )
        
        session = self.Session()
        db_model = DatasetVersionModel(
            version_id=version.version_id,
            spec_id=version.spec_id,
            data_location=version.data_location,
            metadata_json=version.metadata.model_dump(),
            lineage_json=version.lineage.model_dump(),
            created_at=version.created_at
        )
        session.add(db_model)
        session.commit()
        session.close()
        
        return version

    def get_version(self, version_id: str) -> DatasetVersion:
        session = self.Session()
        model = session.query(DatasetVersionModel).filter_by(version_id=version_id).first()
        session.close()
        if not model:
            raise ValueError(f"Version {version_id} not found")
            
        return DatasetVersion(
            version_id=model.version_id,
            spec_id=model.spec_id,
            data_location=model.data_location,
            metadata=DatasetMetadata(**model.metadata_json),
            lineage=DatasetLineage(**model.lineage_json),
            created_at=model.created_at
        )

    def query_datasets(self, filters: QueryFilters) -> List[DatasetVersion]:
        session = self.Session()
        query = session.query(DatasetVersionModel)
        
        if filters.spec_id:
            query = query.filter_by(spec_id=filters.spec_id)
        if filters.created_after:
            query = query.filter(DatasetVersionModel.created_at >= filters.created_after)
            
        models = query.all()
        session.close()
        
        return [
            DatasetVersion(
                version_id=m.version_id,
                spec_id=m.spec_id,
                data_location=m.data_location,
                metadata=DatasetMetadata(**m.metadata_json),
                lineage=DatasetLineage(**m.lineage_json),
                created_at=m.created_at
            )
            for m in models
        ]
        
    def generate_artifacts(self, version: DatasetVersion, formats: List[str]) -> OutputArtifacts:
        output_dir = os.path.join(self.storage_dir, version.version_id, "artifacts")
        os.makedirs(output_dir, exist_ok=True)
        
        data_path = os.path.join(version.data_location, "data.json")
        with open(data_path, "r") as f:
            records = json.load(f)
            
        import pandas as pd
        df = pd.DataFrame(records)
        dataset_files = {}
        
        if "csv" in formats:
            csv_path = os.path.join(output_dir, "dataset.csv")
            if not df.empty:
                df.to_csv(csv_path, index=False)
            else:
                with open(csv_path, "w") as f: pass
            dataset_files["csv"] = csv_path
            
        if "parquet" in formats:
            parquet_path = os.path.join(output_dir, "dataset.parquet")
            if not df.empty:
                df.to_parquet(parquet_path, index=False)
            else:
                with open(parquet_path, "w") as f: pass
            dataset_files["parquet"] = parquet_path
            
        meta_path = os.path.join(output_dir, "metadata.json")
        with open(meta_path, "w") as f:
            f.write(version.metadata.model_dump_json(indent=2))
            
        schema_path = os.path.join(output_dir, "schema.json")
        with open(schema_path, "w") as f:
            f.write(json.dumps({"fields": list(df.columns)}))
            
        quality_path = os.path.join(output_dir, "quality_report.json")
        with open(quality_path, "w") as f:
            f.write(version.metadata.quality_metrics.model_dump_json())
            
        mermaid_path = os.path.join(output_dir, "pipeline_workflow.md")
        with open(mermaid_path, "w") as f:
            f.write("# Dataset Pipeline Lineage\n\n")
            f.write("```mermaid\ngraph TD;\n")
            f.write("    Start((Raw Sources)) --> Ingest;\n")
            
            # Use metadata processing history if available, else generic
            history = version.metadata.processing_history or []
            if not history:
                f.write("    Ingest --> Clean;\n")
                f.write("    Clean --> Transform;\n")
                f.write("    Transform --> QualityAnalysis;\n")
                f.write("    QualityAnalysis --> ArtifactGeneration;\n")
            else:
                prev_node = "Ingest"
                for i, step in enumerate(history):
                    node_name = step.stage.replace(" ", "")
                    # E.g., Clean --> Transform
                    f.write(f"    {prev_node} --> {node_name}['{step.stage} - {step.description}'];\n")
                    prev_node = node_name
                    
            f.write("```\n")
            
        archive_path = os.path.join(output_dir, "dataset_archive.tar.gz")
        with tarfile.open(archive_path, "w:gz") as tar:
            for file_name in os.listdir(output_dir):
                if file_name != "dataset_archive.tar.gz":
                    tar.add(os.path.join(output_dir, file_name), arcname=file_name)
            
        return OutputArtifacts(
            dataset_files=dataset_files,
            metadata_file=meta_path,
            schema_file=schema_path,
            quality_report_file=quality_path,
            archive_path=archive_path
        )
