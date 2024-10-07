from datetime import datetime, timedelta
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime, func, Boolean
from quart_auth import AuthUser
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

Base = declarative_base()

class Device(Base):
    __tablename__ = 'devices'

    id = Column(Integer, primary_key=True)
    hardware_id = Column(String(200), nullable=False, index=True, unique=True)
    device_name = Column(String(50), nullable=False)
    os_version = Column(String(100), nullable=False)
    geo_location = Column(String(100))
    installed_apps = Column(Text)
    timestamp = Column(DateTime, default=func.current_timestamp())
    last_heartbeat = Column(DateTime)
    can_view_info = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)

    def is_online(self):
        return self.last_heartbeat and (datetime.utcnow() - self.last_heartbeat) < timedelta(seconds=60)

    def __repr__(self):
        return f"<Device {self.device_name}>"


class User(Base, AuthUser):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(150), nullable=False)

    @property
    def auth_id(self):
        return self.username

    def set_password(self, password):
        # Use bcrypt to hash passwords
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        # Check if the given password matches the stored hashed password
        return bcrypt.check_password_hash(self.password_hash, password)
