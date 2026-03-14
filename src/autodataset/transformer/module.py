import pandas as pd
from typing import List, Dict, Callable, Any
from pydantic import BaseModel

from autodataset.models.data import RawData
from autodataset.models.specifications import TransformationConfig, EncodingMethod, FeatureRule


class TransformFunction(BaseModel):
    name: str
    description: str

class TransformationLogEntry(BaseModel):
    transformation_type: str
    features_affected: List[str]
    parameters: Dict[str, Any]

class TransformationResult(BaseModel):
    transformed_data: RawData
    transformation_log: List[TransformationLogEntry]

class DataTransformer:
    def transform(self, data: RawData, config: TransformationConfig) -> TransformationResult:
        if not data.records:
            return TransformationResult(transformed_data=data, transformation_log=[])
            
        df = pd.DataFrame(data.records)
        log = []
        
        # Encoding
        if config.encoding_method:
            cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
            if cat_cols:
                if config.encoding_method == EncodingMethod.ONE_HOT:
                    df = pd.get_dummies(df, columns=cat_cols)
                elif config.encoding_method == EncodingMethod.LABEL:
                    for col in cat_cols:
                        df[col] = df[col].astype('category').cat.codes
                elif config.encoding_method == EncodingMethod.TARGET:
                    # simplistic mock target encoding
                    pass
                log.append(TransformationLogEntry(
                    transformation_type="encoding",
                    features_affected=cat_cols,
                    parameters={"method": config.encoding_method.value}
                ))
                
        # Feature rules
        if config.feature_rules:
            for rule in config.feature_rules:
                if rule.rule_type == "polynomial":
                    deg = rule.parameters.get("degree", 2)
                    if rule.feature_name in df.columns:
                        new_col = f"{rule.feature_name}_poly_{deg}"
                        df[new_col] = df[rule.feature_name] ** deg
                        log.append(TransformationLogEntry(
                            transformation_type="polynomial",
                            features_affected=[rule.feature_name, new_col],
                            parameters={"degree": deg}
                        ))
                elif rule.rule_type == "binning":
                    bins = rule.parameters.get("bins", 5)
                    if rule.feature_name in df.columns:
                        new_col = f"{rule.feature_name}_binned"
                        df[new_col] = pd.cut(df[rule.feature_name], bins=bins, labels=False)
                        log.append(TransformationLogEntry(
                            transformation_type="binning",
                            features_affected=[rule.feature_name, new_col],
                            parameters={"bins": bins}
                        ))
                        
        new_records = df.to_dict(orient='records')
        new_data = RawData(records=new_records, metadata=data.metadata, format=data.format)
        new_data.metadata.column_count = len(df.columns)
        
        return TransformationResult(transformed_data=new_data, transformation_log=log)
        
    def apply_custom_transformation(self, data: RawData, func: Callable[[pd.DataFrame], pd.DataFrame]) -> TransformationResult:
        if not data.records:
            return TransformationResult(transformed_data=data, transformation_log=[])
        df = pd.DataFrame(data.records)
        df_new = func(df)
        new_records = df_new.to_dict(orient='records')
        new_data = RawData(records=new_records, metadata=data.metadata, format=data.format)
        new_data.metadata.column_count = len(df_new.columns)
        log = [TransformationLogEntry(
            transformation_type="custom",
            features_affected=list(df_new.columns),
            parameters={}
        )]
        return TransformationResult(transformed_data=new_data, transformation_log=log)
