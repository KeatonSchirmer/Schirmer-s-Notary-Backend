from datetime import datetime
from database.db import db
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey, Enum, Numeric

class Finance(db.Model):
    __tablename__ = "finances"

    id = Column(Integer, primary_key=True)
    type = Column(Enum("earning", "expense", name="finance_type"), nullable=False)
    category = Column(String(100), nullable=False)  # e.g. Loan Signing, Subscription
    description = Column(Text, nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "category": self.category,
            "description": self.description,
            "amount": float(self.amount),
            "date": self.date.strftime("%Y-%m-%d"),
            "created_at": self.created_at.isoformat()
        }