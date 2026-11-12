import uuid

from sqlalchemy.dialects.postgresql import UUID

from backend.database import db


class Alert(db.Model):
    """Safety alert emitted when a monitored child transitions into warning or danger."""

    __tablename__ = "alerts"

    alert_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guardian_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("guardian.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    child_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("child.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    base_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("bases.base_id", ondelete="CASCADE"),
        nullable=False,
    )
    alert_type = db.Column(db.String(20), nullable=False)
    distance_meters = db.Column(db.Float, nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.current_timestamp())
    resolved_at = db.Column(db.DateTime, nullable=True)

    guardian = db.relationship("Guardian", back_populates="alerts")
    child = db.relationship("Child", back_populates="alerts")
    base = db.relationship("Bases", back_populates="alerts")

    def to_dict(self):
        return {
            "alert_id": str(self.alert_id),
            "guardian_id": str(self.guardian_id),
            "child_id": str(self.child_id),
            "child_username": self.child.user.username if self.child and self.child.user else None,
            "base_id": str(self.base_id),
            "base_name": self.base.base_name if self.base else None,
            "alert_type": self.alert_type,
            "distance_meters": round(self.distance_meters, 2),
            "message": self.message,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }
