from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String) # For local auth
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    auth_source = Column(String, default="local") # 'local' or 'ldap'

class Worker(Base):
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String, unique=True, index=True)
    hostname = Column(String)
    ip_address = Column(String)
    status = Column(String, default="offline") # online, offline, busy
    capabilities = Column(JSON) # List of capabilities e.g. ["run_command", "robot"]
    last_heartbeat = Column(DateTime, default=datetime.utcnow)

class TestResult(Base):
    __tablename__ = "test_results"

    id = Column(Integer, primary_key=True, index=True)
    suite_name = Column(String, index=True)
    total_tests = Column(Integer)
    passed_tests = Column(Integer)
    failed_tests = Column(Integer)
    skipped_tests = Column(Integer)
    execution_time = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    report_path = Column(String) # Path to the generated report
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=True)

    worker = relationship("Worker")
