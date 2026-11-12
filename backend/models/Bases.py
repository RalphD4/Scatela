import uuid

from sqlalchemy.dialects.postgresql import UUID

from backend.database import db


class Bases(db.Model):
    """Guardian-defined safety base location with warning and danger radii in meters."""

    __tablename__ = "bases"

    base_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("guardian.user_id"), nullable=False)
    base_name = db.Column(db.Text, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    warning_radius = db.Column(db.Integer, nullable=False)
    danger_radius = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.current_timestamp())

    guardian = db.relationship("Guardian", back_populates="bases")
    child_statuses = db.relationship(
        "ChildBaseStatus",
        back_populates="base",
        cascade="all, delete-orphan",
    )
    alerts = db.relationship("Alert", back_populates="base", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "base_id": str(self.base_id),
            "user_id": str(self.user_id),
            "base_name": self.base_name,
            "longitude": self.longitude,
            "latitude": self.latitude,
            "warning_radius": self.warning_radius,
            "danger_radius": self.danger_radius,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
