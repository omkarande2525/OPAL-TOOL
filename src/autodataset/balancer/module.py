import pandas as pd
import numpy as np
from typing import Dict, Optional, Any
from pydantic import BaseModel

from autodataset.models.data import RawData

class BalancingReport(BaseModel):
    original_distribution: Dict[str, int]
    target_distribution: Dict[str, int]
    final_distribution: Dict[str, int]
    strategy_used: str

class BalancingResult(BaseModel):
    balanced_data: RawData
    final_distribution: Dict[str, int]
    balancing_report: BalancingReport

class ClassBalancer:
    def balance(self, data: RawData, target_variable: str, constraints: Dict[str, float], target_size: int, strategy: str = "random") -> BalancingResult:
        if not data.records:
            return BalancingResult(
                balanced_data=data,
                final_distribution={},
                balancing_report=BalancingReport(original_distribution={}, target_distribution={}, final_distribution={}, strategy_used=strategy)
            )
            
        df = pd.DataFrame(data.records)
        if target_variable not in df.columns:
            raise ValueError(f"Target variable {target_variable} not found in data")
            
        orig_dist = df[target_variable].value_counts().to_dict()
        
        target_counts = {k: int(np.round(v * target_size)) for k, v in constraints.items()}
        
        balanced_dfs = []
        for class_label, t_count in target_counts.items():
            class_df = df[df[target_variable] == class_label]
            c_count = len(class_df)
            
            if c_count == 0:
                continue
                
            if c_count > t_count:
                if strategy == "random":
                    balanced_dfs.append(self.undersample(class_df, t_count))
                else: 
                    balanced_dfs.append(self.undersample(class_df, t_count))
            elif c_count < t_count:
                if strategy == "random":
                    balanced_dfs.append(self.oversample(class_df, t_count))
                elif strategy == "smote":
                    balanced_dfs.append(self.generate_synthetic(df, class_label, target_variable, t_count))
                else:
                    balanced_dfs.append(self.oversample(class_df, t_count))
            else:
                balanced_dfs.append(class_df)
                
        final_df = pd.concat(balanced_dfs, ignore_index=True)
        final_dist = final_df[target_variable].value_counts().to_dict()
        
        new_records = final_df.to_dict(orient='records')
        new_data = RawData(records=new_records, metadata=data.metadata, format=data.format)
        new_data.metadata.record_count = len(new_records)
        
        report = BalancingReport(
            original_distribution=orig_dist,
            target_distribution=target_counts,
            final_distribution=final_dist,
            strategy_used=strategy
        )
        
        return BalancingResult(
            balanced_data=new_data,
            final_distribution=final_dist,
            balancing_report=report
        )

    def oversample(self, class_df: pd.DataFrame, target_count: int) -> pd.DataFrame:
        return class_df.sample(n=target_count, replace=True)
        
    def undersample(self, class_df: pd.DataFrame, target_count: int) -> pd.DataFrame:
        return class_df.sample(n=target_count, replace=False)
        
    def generate_synthetic(self, full_df: pd.DataFrame, class_label: Any, target_variable: str, target_count: int) -> pd.DataFrame:
        class_df = full_df[full_df[target_variable] == class_label]
        # Simple fallback for SMOTE in mock representation
        return class_df.sample(n=target_count, replace=True)
