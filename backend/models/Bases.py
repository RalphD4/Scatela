from backend.database import db
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Bases(db.model):
    base_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.user_id"), primary_key=True)
    base_name = db.Column(db.Text, nullable=False)
    longitude = db.Column(db.float, nullable=False)
    latitude = db.Column(db.flaot, nullable=False)

    warning_radius = db.Column(db.Float, nullable=False)
    danger_radius = db.Column(db.Float, nullable=False)

    

