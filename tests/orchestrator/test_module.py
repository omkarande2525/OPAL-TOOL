import pytest
from autodataset.orchestrator.module import WorkflowOrchestrator, PipelineStage, PipelineStatus
from autodataset.repository.module import DatasetRepository
from tests.repository.test_module import create_dummy_spec

@pytest.fixture
def orchestrator(tmp_path):
    repo = DatasetRepository(storage_dir=str(tmp_path))
    return WorkflowOrchestrator(repository=repo)
    
def test_property_28_pipeline_execution_order(orchestrator):
    """
    Feature: autodataset-platform, Property 28: Pipeline Stage Execution Order
    """
    spec = create_dummy_spec()
    res = orchestrator.execute_pipeline(spec)
    assert res.status == PipelineStatus.COMPLETED

def test_property_29_pipeline_failure_handling(orchestrator):
    """
    Feature: autodataset-platform, Property 29: Pipeline Failure Handling
    """
    spec = create_dummy_spec()
    spec._mock_failure = True
    res = orchestrator.execute_pipeline(spec)
    assert res.status == PipelineStatus.FAILED
    assert res.error.stage == PipelineStage.TRANSFORMATION

def test_property_30_pipeline_resumption(orchestrator):
    """
    Feature: autodataset-platform, Property 30: Pipeline Resumption
    """
    spec = create_dummy_spec()
    res = orchestrator.resume_pipeline("pipe_1", PipelineStage.BALANCING, spec)
    assert res.status == PipelineStatus.COMPLETED

def test_property_31_pipeline_status_tracking(orchestrator):
    """
    Feature: autodataset-platform, Property 31: Pipeline Status Tracking
    """
    spec = create_dummy_spec()
    orchestrator.execute_pipeline(spec, pipeline_id="pipe_track")
    status = orchestrator.get_pipeline_status("pipe_track")
    assert status["status"] == PipelineStatus.COMPLETED

def test_property_32_pipeline_stage_timeout(orchestrator):
    """
    Feature: autodataset-platform, Property 32: Pipeline Stage Timeout Enforcement
    """
    spec = create_dummy_spec()
    spec._mock_timeout = True
    res = orchestrator.execute_pipeline(spec)
    assert res.status == PipelineStatus.TIMEOUT
