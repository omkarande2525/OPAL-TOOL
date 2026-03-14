import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from autodataset.models.data import RawData
from autodataset.models.specifications import QualityThresholds

class AnomalySeverity(str):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class Anomaly(BaseModel):
    feature: str
    anomaly_type: str
    severity: str
    description: str
    indices: List[int]

class AnomalyResult(BaseModel):
    anomalies: List[Anomaly]
    total_anomalies: int

class QualityReport(BaseModel):
    completeness: float
    consistency: float
    accuracy: float
    validity: float
    pass_all_thresholds: bool
    failing_metrics: List[str]

class QualityResult(BaseModel):
    metrics: Dict[str, float]
    passes_thresholds: bool
    quality_report: QualityReport
    anomalies: AnomalyResult

class AnomalyDetector:
    def detect(self, data: RawData) -> AnomalyResult:
        if not data.records:
            return AnomalyResult(anomalies=[], total_anomalies=0)
            
        df = pd.DataFrame(data.records)
        anomalies = []
        
        # Simple Z-score anomaly detection
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                std_v = df[col].std()
                if std_v > 0:
                    z_scores = np.abs((df[col] - df[col].mean()) / std_v)
                    high_severity = df[z_scores > 3.5].index.tolist()
                    med_severity = df[(z_scores > 2.5) & (z_scores <= 3.5)].index.tolist()
                    
                    if high_severity:
                        anomalies.append(Anomaly(
                            feature=col,
                            anomaly_type="statistical_outlier",
                            severity=AnomalySeverity.HIGH,
                            description=f"Found {len(high_severity)} high severity outliers (>3.5 std)",
                            indices=high_severity
                        ))
                    if med_severity:
                        anomalies.append(Anomaly(
                            feature=col,
                            anomaly_type="statistical_outlier",
                            severity=AnomalySeverity.MEDIUM,
                            description=f"Found {len(med_severity)} medium severity outliers (>2.5 std)",
                            indices=med_severity
                        ))
                        
        total = sum(len(a.indices) for a in anomalies)
        return AnomalyResult(anomalies=anomalies, total_anomalies=total)

class QualityAnalyzer:
    def __init__(self):
        self.detector = AnomalyDetector()
        
    def analyze(self, data: RawData, thresholds: QualityThresholds) -> QualityResult:
        df = pd.DataFrame(data.records) if data.records else pd.DataFrame()
        
        # Great Expectations Integration
        import great_expectations as gx
        
        context = gx.get_context(mode="ephemeral")
        suite_name = "autodataset_quality_suite"
        suite = context.suites.add(gx.ExpectationSuite(name=suite_name))
        
        expected_completeness = thresholds.min_completeness
        
        # Add basic expectations dynamically for every column
        if not df.empty:
            for col in df.columns:
                # Expect minimum completeness (not null) for each column based on the threshold
                # Note: mostly (0.99) vs purely threshold (e.g. 0.8)
                suite.add_expectation(
                    gx.expectations.ExpectColumnValuesToNotBeNull(
                        column=col,
                        mostly=expected_completeness
                    )
                )
                
        # Validate data
        batch_request = None
        validation_result = None
        
        passes = True
        comp = 1.0
        cons = 1.0
        acc = 1.0
        val = 1.0
        failing_metrics = []
        
        if not df.empty:
            # GE 1.x validation via context DataSources
            datasource = context.data_sources.add_pandas("pandas_datasource")
            data_asset = datasource.add_dataframe_asset("data")
            batch_request = data_asset.build_batch_request(dataframe=df)
            
            checkpoint = context.checkpoints.add(
                gx.Checkpoint(
                    name="quality_checkpoint",
                    validation_definitions=[
                        gx.ValidationDefinition(
                            name="quality_validation",
                            data=batch_request,
                            suite=suite
                        )
                    ]
                )
            )
            validation_results = checkpoint.run()
            # Extract basic metric logic from results
            # For simplicity in output report, map pass/fail
            if not validation_results.success:
                passes = False
                failing_metrics.append("great_expectations_suite_failed")
                
            # Keep manual pandas fallback for exact metric reporting
            comp = self.compute_completeness(df)
            cons = self.compute_consistency(df)
            acc = self.compute_accuracy(df)

        anomaly_result = self.detector.detect(data)
        anomaly_rate = anomaly_result.total_anomalies / len(df) if len(df) > 0 else 0.0
        
        if anomaly_rate > thresholds.max_anomaly_rate:
            failing_metrics.append(f"anomaly_rate={anomaly_rate}")
            passes = False
            
        report = QualityReport(
            completeness=comp,
            consistency=cons,
            accuracy=acc,
            validity=val,
            pass_all_thresholds=passes,
            failing_metrics=failing_metrics
        )
        
        metrics = {
            "completeness": comp,
            "consistency": cons,
            "accuracy": acc,
            "validity": val,
            "anomaly_rate": anomaly_rate
        }
        
        return QualityResult(
            metrics=metrics,
            passes_thresholds=passes,
            quality_report=report,
            anomalies=anomaly_result
        )
        
    def compute_completeness(self, df: pd.DataFrame) -> float:
        if df.empty: return 1.0
        total_cells = df.size
        non_null = df.count().sum()
        return non_null / total_cells if total_cells > 0 else 1.0
        
    def compute_consistency(self, df: pd.DataFrame) -> float:
        return 1.0
        
    def compute_accuracy(self, df: pd.DataFrame) -> float:
        return 1.0

