import pandas as pd
from typing import List, Dict, Callable, Any, Optional
from pydantic import BaseModel

from autodataset.models.data import RawData

class LabelingRule(BaseModel):
    rule_name: str
    description: str

class LabelingConfig(BaseModel):
    labeling_rules: List[LabelingRule]
    target_variable: str
    confidence_threshold: float = 0.8

class LabelingReport(BaseModel):
    total_records: int
    labeled_records: int
    success_percentage: float
    average_confidence: Optional[float]

class LabelingResult(BaseModel):
    labeled_data: RawData
    labeling_report: LabelingReport
    confidence_scores: Optional[List[float]]

class LabelingEngine:
    def label(self, data: RawData, config: LabelingConfig, rule_functions: Dict[str, Callable[[pd.Series], Any]]) -> LabelingResult:
        if not data.records:
            return LabelingResult(
                labeled_data=data,
                labeling_report=LabelingReport(total_records=0, labeled_records=0, success_percentage=0.0, average_confidence=None),
                confidence_scores=None
            )
            
        df = pd.DataFrame(data.records)
        target = config.target_variable
        
        # Apply rules sequentially
        labels = [None] * len(df)
        confidences = [0.0] * len(df)
        
        for i, row in df.iterrows():
            best_label = None
            highest_conf = 0.0
            
            for rule in config.labeling_rules:
                if rule.rule_name in rule_functions:
                    func = rule_functions[rule.rule_name]
                    res = func(row)
                    if res:
                        label, conf = res
                        if conf > highest_conf:
                            highest_conf = conf
                            best_label = label
                            
            if highest_conf >= config.confidence_threshold:
                labels[i] = best_label
                confidences[i] = highest_conf
                
        df[target] = labels
        
        labeled_count = sum(1 for label in labels if pd.notna(label))
        success_perc = (labeled_count / len(df)) * 100 if len(df) > 0 else 0.0
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        
        new_records = df.to_dict(orient='records')
        new_data = RawData(records=new_records, metadata=data.metadata, format=data.format)
        new_data.metadata.column_count = len(df.columns)
        
        report = LabelingReport(
            total_records=len(df),
            labeled_records=labeled_count,
            success_percentage=success_perc,
            average_confidence=avg_conf
        )
        
        return LabelingResult(
            labeled_data=new_data,
            labeling_report=report,
            confidence_scores=confidences
        )
        
    def validate_labels(self, data: RawData, target_variable: str, valid_labels: List[Any]) -> bool:
        if not data.records:
            return True
        df = pd.DataFrame(data.records)
        if target_variable not in df.columns:
            return False
            
        return df[target_variable].dropna().isin(valid_labels).all()
