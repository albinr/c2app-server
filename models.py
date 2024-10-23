from datetime import datetime, timedelta
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, String, Text, DateTime, func, Boolean, ForeignKey
from quart_auth import AuthUser
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

Base = declarative_base()

class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True)
    hardware_id = Column(String(200), nullable=False, index=True, unique=True)
    device_name = Column(String(50), nullable=False)
    os_version = Column(String(100), nullable=False)
    geo_location = Column(String(100))
    installed_apps = Column(Text)
    timestamp = Column(DateTime, default=func.current_timestamp())
    last_heartbeat = Column(DateTime)
    on_watchlist = Column(Boolean, default=True)
    rejoin_requested = Column(Boolean, default=False)
    can_view_info = Column(Boolean, default=False)

    # device_requests = relationship("DeviceRequest", back_populates="device")
    device_requests = relationship("DeviceRequest", back_populates="device", cascade="all, delete-orphan")

    def is_online(self):
        return self.last_heartbeat and (datetime.utcnow() - self.last_heartbeat) < timedelta(seconds=60)

    def __repr__(self):
        return f"<Device {self.device_name}>"
    

class DeviceRequest(Base):
    __tablename__ = "device_requests"
    id = Column(Integer, primary_key=True)
    # device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    request_timestamp = Column(DateTime, default=func.current_timestamp())
    status = Column(String(50), default="pending")  # "pending", "approved" or "denied"
    resolved = Column(Boolean, default=False)
    resolved_timestamp = Column(DateTime)
    request_type = Column(String(50), nullable=False)  # "rejoin_watchlist" or "command_execution", etc.

    device = relationship("Device", back_populates="device_requests")

    def __repr__(self):
        return f"<RejoinRequest for Device ID {self.device_id}, Status: {self.status}>"


class User(Base, AuthUser):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(150), nullable=False)

    @property
    def auth_id(self):
        return self.username

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)
