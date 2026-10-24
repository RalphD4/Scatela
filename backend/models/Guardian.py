from backend.database import db
from sqlalchemy.dialects.postgresql import UUID


class Guardian(db.Model):
    __tablename__ = "guardian"

    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.user_id"), primary_key=True)
    longitude = db.Column(db.Float), nullable=False
    latitude = db.Column(db.Float), nullable=False