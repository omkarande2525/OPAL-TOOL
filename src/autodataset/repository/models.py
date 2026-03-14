from sqlalchemy import Column, String, Float, DateTime, JSON, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class DatasetVersionModel(Base):
    __tablename__ = 'dataset_versions'
    
    version_id = Column(String, primary_key=True)
    spec_id = Column(String, index=True)
    data_location = Column(String)
    metadata_json = Column(JSON)
    lineage_json = Column(JSON)
    created_at = Column(DateTime)
