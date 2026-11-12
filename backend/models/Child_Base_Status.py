from sqlalchemy.dialects.postgresql import UUID

from backend.database import db


class ChildBaseStatus(db.Model):
    """Latest evaluated monitoring status for a (child, base) pair to detect state transitions."""

    __tablename__ = "child_base_status"

    child_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("child.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    base_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("bases.base_id", ondelete="CASCADE"),
        primary_key=True,
    )
    status = db.Column(db.String(20), nullable=False)
    distance_meters = db.Column(db.Float, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.func.current_timestamp())

    child = db.relationship("Child", back_populates="base_statuses")
    base = db.relationship("Bases", back_populates="child_statuses")

    def to_dict(self):
        return {
            "child_id": str(self.child_id),
            "base_id": str(self.base_id),
            "status": self.status,
            "distance_meters": round(self.distance_meters, 2),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
