import uuid

from sqlalchemy.dialects.postgresql import UUID

from backend.database import db


class Child_Log(db.Model):
    """Historical coordinate log entry for a child user."""

    __tablename__ = "child_log"

    log_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    child_id = db.Column(UUID(as_uuid=True), db.ForeignKey("child.user_id"), nullable=False)
    longitude = db.Column(db.Float, nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.current_timestamp())

    child = db.relationship("Child", back_populates="logs")

    def to_dict(self):
        return {
            "log_id": str(self.log_id),
            "child_id": str(self.child_id),
            "longitude": self.longitude,
            "latitude": self.latitude,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
