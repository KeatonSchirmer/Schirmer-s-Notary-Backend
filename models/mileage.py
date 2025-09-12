from database.db import db
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from datetime import datetime

class Mileage(db.Model):
    __tablename__ = "mileage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # links to your User model
    date = Column(DateTime, default=datetime.utcnow, nullable=False)
    miles = Column(Float, nullable=False)
    purpose = Column(String(255), nullable=True)  # e.g., "Client Meeting", "Office Visit"
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Mileage {self.miles} miles on {self.date}>"