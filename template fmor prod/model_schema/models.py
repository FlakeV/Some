import uuid
import datetime
import sqlalchemy as sa

from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Float, DECIMAL, String, VARCHAR, BIGINT, TIMESTAMP, DateTime, ForeignKey
from geoalchemy2 import Geometry
from sqlalchemy.orm import scoped_session, sessionmaker, relationship, backref
from sqlalchemy.sql import func


class FileUploadRecord(Base):
    __tablename__ = "file_upload_records"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    file_name_orig = Column(String)
    file_name_uuid = Column(String)
    file_type = Column(String)  # shape(zip) / geojson / kml
    file_path = Column(String)
    upload_context = Column(String)  # plots / harvest / others
    customer_id = Column(UUID(as_uuid=True), nullable=True)
    status = Column(VARCHAR, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.utcnow())
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.datetime.utcnow, server_default=func.utcnow())


class PlotsUploadSession():
    __tablename__ = "plots_upload_session"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    customer_id = Column(UUID, nullable=False)
    file_upload_record_id = Column(UUID)
    attribute_mapping_json = Column(JSONB)
    plots_setup_stage = Column(VARCHAR)
    created_at = Column(DateTime(timezone=True), server_default=func.utcnow())
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.datetime.utcnow, server_default=func.utcnow())


class DraftPlot():
    __tablename__ = "draft_plots"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    name = Column(String(collation='default'), nullable=True)
    plots_upload_session_id = Column(UUID, nullable=False)
    location_name = Column(String(collation='default'), nullable=True)
    geometry = Column(Geometry(srid=Constants.CRS_WGS84))
    area = Column(Float, nullable=True)
    altitude = Column(Float, nullable=True)
    grape_type = Column(VARCHAR(collation='default'), nullable=True)
    soil_type = Column(VARCHAR(collation='default'), nullable=True)
    facing = Column(VARCHAR(collation='default'), nullable=True)
    row_spacing = Column(Float, nullable=True)
    vine_spacing = Column(Float, nullable=True)
    flow_rate = Column(Float, nullable=True)
    vendor_name = Column(String(collation='default'), nullable=True)
    farmer_name = Column(String(collation='default'), nullable=True)
    region_code = Column(VARCHAR(collation='default'), nullable=True)
    city_id = Column(UUID(as_uuid=True), nullable=True)
    plot_foundation_year = Column(Integer, nullable=True)
    phenological_cycle = Column(VARCHAR(collation='default'), nullable=True)
    status = Column(VARCHAR(collation='default'), nullable=True)
    attributes_json_dump = Column(JSONB, nullable=True)
    uploaded_by = Column(UUID(as_uuid=True), nullable=True)
    customer_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.utcnow())
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.datetime.utcnow, server_default=func.utcnow())


class PlotSearchParams():
    def __init__(self):
        self.name = None
        self.location_name = None
        self.city_id = None
        self.customer_id = None
        self.grape_type = None
        self.soil_type = None
        self.altitude = None
        self.vendor_name = None
        self.farmer_name = None
