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
        
        comp = self.compute_completeness(df)
        cons = self.compute_consistency(df)
        acc = self.compute_accuracy(df)
        val = 1.0 # placeholder for validity metric
        
        anomaly_result = self.detector.detect(data)
        anomaly_rate = anomaly_result.total_anomalies / len(df) if len(df) > 0 else 0.0
        
        failing_metrics = []
        if comp < thresholds.min_completeness: failing_metrics.append(f"completeness={comp}")
        if cons < thresholds.min_consistency: failing_metrics.append(f"consistency={cons}")
        if acc < thresholds.min_accuracy: failing_metrics.append(f"accuracy={acc}")
        if anomaly_rate > thresholds.max_anomaly_rate: failing_metrics.append(f"anomaly_rate={anomaly_rate}")
        
        passes = len(failing_metrics) == 0
        
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
