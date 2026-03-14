import pandas as pd
import numpy as np
from enum import Enum
from typing import List, Dict, Optional
from pydantic import BaseModel

from autodataset.models.data import RawData

class MissingValueStrategy(str, Enum):
    REMOVE = "remove"
    IMPUTE_MEAN = "impute_mean"
    IMPUTE_MEDIAN = "impute_median"
    FORWARD_FILL = "forward_fill"

class NormalizationMethod(str, Enum):
    MIN_MAX = "min_max"
    Z_SCORE = "z_score"

class OutlierMethod(str, Enum):
    IQR = "iqr"
    Z_SCORE = "z_score"

class NormalizationConfig(BaseModel):
    features: List[str]
    method: NormalizationMethod
    
class OutlierConfig(BaseModel):
    features: List[str]
    method: OutlierMethod
    threshold: float = 3.0

class CleaningConfig(BaseModel):
    remove_duplicates: bool = True
    missing_value_strategy: MissingValueStrategy = MissingValueStrategy.REMOVE
    normalization_config: Optional[NormalizationConfig] = None
    outlier_config: Optional[OutlierConfig] = None

class ActionLog(BaseModel):
    action: str
    details: str

class CleaningReport(BaseModel):
    records_before: int
    records_after: int
    duplicates_removed: int
    missing_values_handled: int
    outliers_handled: int
    actions: List[ActionLog]

class CleaningResult(BaseModel):
    cleaned_data: RawData
    cleaning_report: CleaningReport

class DataCleaner:
    def clean(self, data: RawData, config: CleaningConfig) -> CleaningResult:
        if not data.records:
            return CleaningResult(
                cleaned_data=data,
                cleaning_report=CleaningReport(
                    records_before=0, records_after=0, duplicates_removed=0,
                    missing_values_handled=0, outliers_handled=0, actions=[]
                )
            )
            
        df = pd.DataFrame(data.records)
        original_records = len(df)
        actions = []
        
        # Remove duplicates
        duplicates_removed = 0
        if config.remove_duplicates:
            before_drop = len(df)
            df = df.drop_duplicates()
            duplicates_removed = before_drop - len(df)
            if duplicates_removed > 0:
                actions.append(ActionLog(action="remove_duplicates", details=f"Removed {duplicates_removed} duplicates"))
                
        # Handle missing values
        missing_handled = int(df.isnull().sum().sum())
        if missing_handled > 0:
            if config.missing_value_strategy == MissingValueStrategy.REMOVE:
                df = df.dropna()
            elif config.missing_value_strategy == MissingValueStrategy.IMPUTE_MEAN:
                df = df.fillna(df.mean(numeric_only=True))
            elif config.missing_value_strategy == MissingValueStrategy.IMPUTE_MEDIAN:
                df = df.fillna(df.median(numeric_only=True))
            elif config.missing_value_strategy == MissingValueStrategy.FORWARD_FILL:
                df = df.ffill()
            actions.append(ActionLog(action="handle_missing", details=f"Strategy: {config.missing_value_strategy}"))
            
        # Normalization
        if config.normalization_config:
            for feat in config.normalization_config.features:
                if feat in df.columns and pd.api.types.is_numeric_dtype(df[feat]):
                    if config.normalization_config.method == NormalizationMethod.MIN_MAX:
                        min_v = df[feat].min()
                        max_v = df[feat].max()
                        if max_v != min_v:
                            df[feat] = (df[feat] - min_v) / (max_v - min_v)
                    elif config.normalization_config.method == NormalizationMethod.Z_SCORE:
                        mean_v = df[feat].mean()
                        std_v = df[feat].std()
                        if std_v != 0:
                            df[feat] = (df[feat] - mean_v) / std_v
            actions.append(ActionLog(action="normalize", details=f"Method: {config.normalization_config.method.value}"))
            
        # Handle outliers
        outliers_handled = 0
        if config.outlier_config:
            for feat in config.outlier_config.features:
                if feat in df.columns and pd.api.types.is_numeric_dtype(df[feat]):
                    before_outliers = len(df)
                    if config.outlier_config.method == OutlierMethod.Z_SCORE:
                        # Prevent div by zero
                        std_val = df[feat].std()
                        if std_val > 0:
                            z_scores = np.abs((df[feat] - df[feat].mean()) / std_val)
                            df = df[z_scores < config.outlier_config.threshold]
                    elif config.outlier_config.method == OutlierMethod.IQR:
                        Q1 = df[feat].quantile(0.25)
                        Q3 = df[feat].quantile(0.75)
                        IQR = Q3 - Q1
                        df = df[~((df[feat] < (Q1 - 1.5 * IQR)) | (df[feat] > (Q3 + 1.5 * IQR)))]
                    outliers_handled += (before_outliers - len(df))
            if outliers_handled > 0:
                actions.append(ActionLog(action="handle_outliers", details=f"Removed {outliers_handled} outliers"))
            
        new_records = df.to_dict(orient='records')
        new_data = RawData(
            records=new_records,
            metadata=data.metadata,
            format=data.format
        )
        new_data.metadata.record_count = len(new_records)
        
        report = CleaningReport(
            records_before=original_records,
            records_after=len(new_records),
            duplicates_removed=duplicates_removed,
            missing_values_handled=missing_handled,
            outliers_handled=outliers_handled,
            actions=actions
        )
        
        return CleaningResult(cleaned_data=new_data, cleaning_report=report)
