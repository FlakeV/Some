import shapely

from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, fields
from geoalchemy2.shape import to_shape
from geoalchemy2.elements import WKTElement

from .models import FileUploadRecord, DraftPlot, PlotsUploadSession
class FileUploadRecordSchema(BaseSchema):
    class Meta:
        model = FileUploadRecord
        load_instance = True


class PlotsUploadSessionSchema(BaseSchema):
    class Meta:
        model = PlotsUploadSession
        load_instance = True


class DraftPlotSchema(BaseSchema):
    class Meta:
        model = DraftPlot
        load_instance = True
