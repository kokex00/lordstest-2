from datetime import datetime
from app import db
from sqlalchemy import Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship

class Server(db.Model):
    __tablename__ = 'servers'
    
    id = db.Column(Integer, primary_key=True)
    guild_id = db.Column(String(20), unique=True, nullable=False)
    guild_name = db.Column(String(100), nullable=False)
    log_channel_id = db.Column(String(20))
    activity_channel_id = db.Column(String(20))
    allowed_channels = db.Column(Text)  # JSON array of channel IDs
    created_at = db.Column(DateTime, default=datetime.utcnow)
    
    matches = relationship("Match", back_populates="server", cascade="all, delete-orphan")
    logs = relationship("BotLog", back_populates="server", cascade="all, delete-orphan")

class Match(db.Model):
    __tablename__ = 'matches'
    
    id = db.Column(Integer, primary_key=True)
    server_id = db.Column(Integer, ForeignKey('servers.id'), nullable=False)
    team1 = db.Column(String(200), nullable=False)
    team2 = db.Column(String(200), nullable=False)
    match_date = db.Column(DateTime, nullable=False)
    role_mentions = db.Column(Text)  # JSON array of role IDs
    channel_id = db.Column(String(20), nullable=False)
    message_id = db.Column(String(20))
    is_active = db.Column(Boolean, default=True)
    created_by = db.Column(String(20), nullable=False)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    
    server = relationship("Server", back_populates="matches")
    reminders = relationship("MatchReminder", back_populates="match", cascade="all, delete-orphan")

class MatchReminder(db.Model):
    __tablename__ = 'match_reminders'
    
    id = db.Column(Integer, primary_key=True)
    match_id = db.Column(Integer, ForeignKey('matches.id'), nullable=False)
    reminder_time = db.Column(DateTime, nullable=False)
    reminder_type = db.Column(String(20), nullable=False)  # '10min' or '3min'
    sent = db.Column(Boolean, default=False)
    
    match = relationship("Match", back_populates="reminders")

class BotLog(db.Model):
    __tablename__ = 'bot_logs'
    
    id = db.Column(Integer, primary_key=True)
    server_id = db.Column(Integer, ForeignKey('servers.id'), nullable=False)
    user_id = db.Column(String(20), nullable=False)
    username = db.Column(String(50), nullable=False)
    command = db.Column(String(100), nullable=False)
    channel_id = db.Column(String(20), nullable=False)
    details = db.Column(Text)
    timestamp = db.Column(DateTime, default=datetime.utcnow)
    
    server = relationship("Server", back_populates="logs")

class Translation(db.Model):
    __tablename__ = 'translations'
    
    id = db.Column(Integer, primary_key=True)
    key = db.Column(String(100), nullable=False)
    language = db.Column(String(10), nullable=False)
    text = db.Column(Text, nullable=False)
    
    __table_args__ = (db.UniqueConstraint('key', 'language'),)
