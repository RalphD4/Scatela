from backend.database import db

from sqlalchemy.dialects.postgresql import UUID
import uuid

class Child_Log(db.Model):
    log_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    child_id = db.Column(UUID(as_uuid=True), db.ForeignKey("child.user_id"))
    longitude = db.Column(db.float, nullable=False)
    latitude = db.Column(db.flaot, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.current_timestamp())

    