from database.db import db

from sqlalchemy import Column, Integer, String, Float, DateTime, Text

class SystemSetting(db.Model):
    __tablename__ = 'system_settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    type = db.Column(db.String(20), nullable=False)

class Backup(db.Model):
    __tablename__ = 'backups'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    size = db.Column(db.String(20))
    created_at = db.Column(db.String(30))
    type = db.Column(db.String(20))

class Service(db.Model):
    __tablename__ = 'services'
    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)

class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    benefits = Column(Text)
    price = Column(Float, nullable=False)

