from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from app.core.database import Base


class ProxyEndpoint(Base):
    __tablename__ = "proxies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False, default=3120)
    username = Column(String(255), nullable=True)
    password_encrypted = Column(Text, nullable=True)
    scheme = Column(String(10), nullable=False, default="http")
    is_enabled = Column(Boolean, nullable=False, default=True)
    weight = Column(Integer, nullable=False, default=1)
    max_concurrency = Column(Integer, nullable=False, default=1)
    region = Column(String(100), nullable=True)
    last_check_at = Column(DateTime, nullable=True)
    last_check_status = Column(String(10), nullable=True)  # ok / failed
    last_exit_ip = Column(String(64), nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
