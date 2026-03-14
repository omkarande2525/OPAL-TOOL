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

class WorkflowOrchestrator:
    def __init__(self, repository: DatasetRepository):
        self.repository = repository
        self.states = {}
        # MLFlow initialization
        mlflow.set_tracking_uri("http://localhost:5000") # We will add this to docker compose later
        mlflow.set_experiment("autodataset_pipelines")
        # OpenLineage
        self.ol_client = OpenLineageClient()
        
    def execute_pipeline(self, spec: DatasetSpecification, pipeline_id: str = None, resume_from: str = None) -> PipelineResult:
        pipeline_id = pipeline_id or f"pipe_{uuid.uuid4().hex[:8]}"
        self.states[pipeline_id] = {"status": PipelineStatus.RUNNING, "current_stage": None}
        
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
                    time.sleep(0.01) # mock execution
                    
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
                    
                    # Mock timeout logic check for Property 32
                    if stage == PipelineStage.CLEANING and getattr(spec, '_mock_timeout', False):
                        self.states[pipeline_id]["status"] = PipelineStatus.TIMEOUT
                        self.ol_client.emit(RunEvent(
                            eventType=RunState.FAIL,
                            eventTime=datetime.now(timezone.utc).isoformat(),
                            run=ol_run,
                            job={"namespace": "autodataset", "name": f"stage_{stage.value}"},
                            inputs=[],
                            outputs=[],
                            producer="https://github.com/autodataset_platform"
                        ))
                        return PipelineResult(pipeline_id=pipeline_id, status=PipelineStatus.TIMEOUT, error=PipelineError(stage=stage.value, error_message="Timeout execution exceeded"))
                        
                    # Mock logic error for Property 29
                    if stage == PipelineStage.TRANSFORMATION and getattr(spec, '_mock_failure', False):
                        raise Exception("Mocked transformation failure")
                        
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
                mlflow.log_param("pipeline_status", "failed")
                mlflow.log_param("failed_stage", stage.value)
                return self._fail_pipeline(pipeline_id, stage.value, str(e))
                
            mlflow.log_param("pipeline_status", "completed")
            # In a real scenario we would log artifact paths to MLflow here
            self.states[pipeline_id]["status"] = PipelineStatus.COMPLETED
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
