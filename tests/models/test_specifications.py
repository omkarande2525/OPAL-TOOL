import pytest
from hypothesis import given, strategies as st
from pydantic import ValidationError
from autodataset.models.specifications import DatasetSpecification, TaskType, QualityThresholds, DataSource, SourceType, DataFormat

@given(
    domain=st.text(min_size=1, max_size=50),
    dataset_size=st.integers(min_value=1, max_value=1_000_000),
    min_comp=st.floats(0.0, 1.0),
    min_cons=st.floats(0.0, 1.0),
    min_acc=st.floats(0.0, 1.0),
    max_anom=st.floats(0.0, 1.0)
)
def test_property_1_specification_validation(domain, dataset_size, min_comp, min_cons, min_acc, max_anom):
    """
    Feature: autodataset-platform, Property 1: Specification Validation Completeness
    """
    valid_data_source = DataSource(
        source_id="src1", source_type=SourceType.WEB, location="http://example.com", format=DataFormat.CSV
    )
    
    spec = DatasetSpecification(
        spec_id="spec1",
        domain=domain,
        task_type=TaskType.CLASSIFICATION,
        target_variable="target",
        dataset_size=dataset_size,
        quality_thresholds=QualityThresholds(
            min_completeness=min_comp, min_consistency=min_cons, min_accuracy=min_acc, max_anomaly_rate=max_anom
        ),
        data_sources=[valid_data_source],
        created_by="tester"
    )
    assert spec is not None
    assert spec.domain == domain
    assert spec.dataset_size == dataset_size

@given(
    class_1_prop=st.floats(0.01, 0.99),
)
def test_property_2_class_balance_validation(class_1_prop):
    """
    Feature: autodataset-platform, Property 2: Class Balance Constraint Validation
    """
    class_2_prop = 1.0 - class_1_prop
    valid_data_source = DataSource(
        source_id="src1", source_type=SourceType.WEB, location="http://example.com", format=DataFormat.CSV
    )
    
    # Valid
    spec = DatasetSpecification(
        spec_id="spec2",
        domain="test",
        task_type=TaskType.CLASSIFICATION,
        target_variable="target",
        dataset_size=1000,
        class_balance_constraints={"class1": class_1_prop, "class2": class_2_prop},
        quality_thresholds=QualityThresholds(
            min_completeness=0.8, min_consistency=0.8, min_accuracy=0.8, max_anomaly_rate=0.1
        ),
        data_sources=[valid_data_source],
        created_by="tester"
    )
    assert spec.class_balance_constraints is not None

    # Invalid
    with pytest.raises(ValidationError) as exc:
        DatasetSpecification(
            spec_id="spec3",
            domain="test",
            task_type=TaskType.CLASSIFICATION,
            target_variable="target",
            dataset_size=1000,
            class_balance_constraints={"class1": 0.5, "class2": 0.6}, # Sum is 1.1
            quality_thresholds=QualityThresholds(
                min_completeness=0.8, min_consistency=0.8, min_accuracy=0.8, max_anomaly_rate=0.1
            ),
            data_sources=[valid_data_source],
            created_by="tester"
        )
    assert "Class balance constraints must sum to 1.0" in str(exc.value)

def test_missing_required_fields():
    with pytest.raises(ValidationError) as exc:
        DatasetSpecification(
            spec_id="spec4",
            domain="test",
            # missing task_type and others
            created_by="tester"
        )
    errors = str(exc.value)
    assert "task_type" in errors
    assert "target_variable" in errors
    assert "quality_thresholds" in errors
    assert "data_sources" in errors

def test_invalid_quality_thresholds():
    valid_data_source = DataSource(
        source_id="src1", source_type=SourceType.WEB, location="http://example.com", format=DataFormat.CSV
    )
    with pytest.raises(ValidationError) as exc:
        DatasetSpecification(
            spec_id="spec",
            domain="test",
            task_type=TaskType.CLASSIFICATION,
            target_variable="target",
            dataset_size=1000,
            quality_thresholds=QualityThresholds(
                min_completeness=1.5, # invalid
                min_consistency=0.8, min_accuracy=0.8, max_anomaly_rate=0.1
            ),
            data_sources=[valid_data_source],
            created_by="tester"
        )
    assert "min_completeness" in str(exc.value)
