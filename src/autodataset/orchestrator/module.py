import structlog
import uuid
import time
from typing import Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel

from autodataset.models.specifications import DatasetSpecification
from autodataset.repository.module import DatasetRepository, OutputArtifacts, DatasetVersion

import mlflow
from openlineage.client import OpenLineageClient, set_producer
from openlineage.client.run import RunEvent, RunState, Run
from openlineage.client.facet import SchemaDatasetFacet

logger = structlog.get_logger()

# Set OpenLineage producer name
set_producer("https://github.com/autodataset_platform")

class PipelineStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

class PipelineStage(str, Enum):
    INGESTION = "ingestion"
    SCHEMA_VALIDATION = "schema_validation"
    CLEANING = "cleaning"
    TRANSFORMATION = "transformation"
    LABELING = "labeling"
    BALANCING = "balancing"
    QUALITY_ANALYSIS = "quality_analysis"
    ARTIFACT_GENERATION = "artifact_generation"

class PipelineError(BaseModel):
    stage: str
    error_message: str

class PipelineResult(BaseModel):
    pipeline_id: str
    status: PipelineStatus
    dataset_version: Optional[DatasetVersion] = None
    artifacts: Optional[OutputArtifacts] = None
    error: Optional[PipelineError] = None

# Prometheus Metrics
from prometheus_client import Counter, Histogram
PIPELINE_RUNS = Counter('pipeline_runs_total', 'Total number of executed pipelines', ['status'])
PIPELINE_DURATION = Histogram('pipeline_duration_seconds', 'Pipeline execution duration in seconds')

class WorkflowOrchestrator:
    def __init__(self, repository: DatasetRepository):
        self.repository = repository
        self.states = {}
        # MLFlow initialization
        mlflow.set_tracking_uri("http://mlflow:5000")
        mlflow.set_experiment("autodataset_pipelines")
        # OpenLineage
        self.ol_client = OpenLineageClient()
        
    def execute_pipeline(self, spec: DatasetSpecification, pipeline_id: str = None, resume_from: str = None) -> PipelineResult:
        pipeline_id = pipeline_id or f"pipe_{uuid.uuid4().hex[:8]}"
        self.states[pipeline_id] = {"status": PipelineStatus.RUNNING, "current_stage": None}
        
        start_time = time.time()
        
        stages_order = [
            PipelineStage.INGESTION,
            PipelineStage.SCHEMA_VALIDATION,
            PipelineStage.CLEANING,
            PipelineStage.TRANSFORMATION,
            PipelineStage.LABELING,
            PipelineStage.BALANCING,
            PipelineStage.QUALITY_ANALYSIS,
            PipelineStage.ARTIFACT_GENERATION
        ]
        
        start_idx = 0
        if resume_from:
            try:
                start_idx = stages_order.index(PipelineStage(resume_from))
            except ValueError:
                return self._fail_pipeline(pipeline_id, resume_from, f"Invalid stage {resume_from}")
                
        # Start MLflow run
        with mlflow.start_run(run_name=f"Pipeline_{pipeline_id}") as run:
            mlflow.log_params({
                "domain": spec.domain,
                "task_type": spec.task_type.value,
                "target_variable": spec.target_variable,
                "dataset_size": spec.dataset_size
            })
            
            try:
                for stage in stages_order[start_idx:]:
                    self.states[pipeline_id]["current_stage"] = stage
                    logger.info(f"Executing stage {stage}", pipeline_id=pipeline_id)
                    
                    # OpenLineage Event Tracking
                    from datetime import datetime, timezone
                    now = datetime.now(timezone.utc).isoformat()
                    run_id = str(uuid.uuid4())
                    
                    ol_run = Run(runId=run_id)
                    
                    self.ol_client.emit(RunEvent(
                        eventType=RunState.START,
                        eventTime=now,
                        run=ol_run,
                        job={"namespace": "autodataset", "name": f"stage_{stage.value}"},
                        inputs=[],
                        outputs=[],
                        producer="https://github.com/autodataset_platform"
                    ))
                    
                    if stage == PipelineStage.INGESTION:
                        from autodataset.ingestion.module import DataIngestionModule
                        ingestion_module = DataIngestionModule()
                        ingestion_result = ingestion_module.ingest(spec.data_sources)
                        if not ingestion_result.raw_data:
                             raise Exception(f"Ingestion failed: {ingestion_result.failed_sources}")
                        # For simplicity in this orchestrated pipeline we handle the primary dataset
                        current_data = ingestion_result.raw_data[0]
                        
                    elif stage == PipelineStage.SCHEMA_VALIDATION:
                        from autodataset.schema_validator.validator import SchemaValidator
                        validator = SchemaValidator()
                        # We don't have a rigid expected schema in the basic spec, so we simply infer or check target.
                        # As per instructions, let's at least enforce the target variable
                        import pandas as pd
                        df = pd.DataFrame(current_data.records)
                        if spec.target_variable not in df.columns:
                            raise ValueError(f"Target column '{spec.target_variable}' missing from ingested data")
                        
                    elif stage == PipelineStage.CLEANING:
                        from autodataset.cleaner.module import DataCleaner, CleaningConfig
                        cleaner = DataCleaner()
                        # Default cleaning config
                        clean_config = CleaningConfig() 
                        clean_result = cleaner.clean(current_data, clean_config)
                        current_data = clean_result.cleaned_data
                        
                    elif stage == PipelineStage.TRANSFORMATION:
                        from autodataset.transformer.module import DataTransformer
                        from autodataset.models.specifications import TransformationConfig
                        transformer = DataTransformer()
                        trans_config = spec.feature_config.transformation_config if spec.feature_config else TransformationConfig()
                        trans_result = transformer.transform(current_data, trans_config)
                        current_data = trans_result.transformed_data
                        
                    elif stage == PipelineStage.LABELING:
                        # Placeholder: No dedicated Labeling Engine defined fully yet in scope
                        pass
                        
                    elif stage == PipelineStage.BALANCING:
                        # Placeholder: No dedicated Balancer defined fully yet in scope
                        pass
                        
                    elif stage == PipelineStage.QUALITY_ANALYSIS:
                        from autodataset.quality.module import QualityAnalyzer
                        analyzer = QualityAnalyzer()
                        quality_result = analyzer.analyze(current_data, spec.quality_thresholds)
                        if not quality_result.passes_thresholds:
                            logger.warning("Quality thresholds not met", failing_metrics=quality_result.quality_report.failing_metrics)
                            # You could conditionally fail here depending on strictness
                            
                    elif stage == PipelineStage.ARTIFACT_GENERATION:
                        from autodataset.models.schemas import Schema
                        from autodataset.models.metadata import DatasetMetadata, DatasetStatistics, QualityMetrics, DatasetLineage
                        import json
                        import pandas as pd
                        
                        df = pd.DataFrame(current_data.records)
                        
                        stats = DatasetStatistics(
                            record_count=len(df),
                            feature_count=len(df.columns)
                        )
                        q_metrics = QualityMetrics(
                            completeness=1.0,
                            consistency=1.0,
                            accuracy=1.0,
                            validity=1.0,
                            anomaly_rate=0.0
                        )
                        lineage = DatasetLineage(
                            source_data_references=[s.source_id for s in spec.data_sources],
                            reproducibility_hash="hash_xyz"
                        )
                        meta = DatasetMetadata(
                            version_id="1.0.0",
                            spec=spec,
                            statistics=stats,
                            quality_metrics=q_metrics,
                            lineage=lineage,
                            processing_time=time.time() - start_time
                        )
                        version = self.repository.create_version(current_data, spec, meta)
                        self.states[pipeline_id]["dataset_version"] = version
                    
                    self.ol_client.emit(RunEvent(
                        eventType=RunState.COMPLETE,
                        eventTime=datetime.now(timezone.utc).isoformat(),
                        run=ol_run,
                        job={"namespace": "autodataset", "name": f"stage_{stage.value}"},
                        inputs=[],
                        outputs=[],
                        producer="https://github.com/autodataset_platform"
                    ))
                        
            except Exception as e:
                logger.exception("Pipeline failed with error", exc_info=e)
                mlflow.log_param("pipeline_status", "failed")
                mlflow.log_param("failed_stage", stage.value)
                duration = time.time() - start_time
                PIPELINE_DURATION.observe(duration)
                PIPELINE_RUNS.labels(status='failed').inc()
                return self._fail_pipeline(pipeline_id, stage.value, str(e))
                
            mlflow.log_param("pipeline_status", "completed")
            # In a real scenario we would log artifact paths to MLflow here
            self.states[pipeline_id]["status"] = PipelineStatus.COMPLETED
            
            duration = time.time() - start_time
            PIPELINE_DURATION.observe(duration)
            PIPELINE_RUNS.labels(status='completed').inc()
            
            return PipelineResult(
                pipeline_id=pipeline_id,
                status=PipelineStatus.COMPLETED
            )
            
    def _fail_pipeline(self, pipeline_id: str, stage: str, error_msg: str) -> PipelineResult:
        self.states[pipeline_id] = {"status": PipelineStatus.FAILED, "error": error_msg}
        return PipelineResult(
            pipeline_id=pipeline_id,
            status=PipelineStatus.FAILED,
            error=PipelineError(stage=stage, error_message=error_msg)
        )
        
    def get_pipeline_status(self, pipeline_id: str):
        return self.states.get(pipeline_id)
        
    def resume_pipeline(self, pipeline_id: str, from_stage: str, spec: DatasetSpecification) -> PipelineResult:
        return self.execute_pipeline(spec, pipeline_id=pipeline_id, resume_from=from_stage)
