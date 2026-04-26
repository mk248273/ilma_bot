from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime, Boolean, create_engine, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import os

# Use DATA_DIR env var for Railway volume support
DATA_DIR = os.getenv("DATA_DIR", ".")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "ilma_bot_v2.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    full_name = Column(String)
    student_id = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    department = Column(String)
    semester = Column(String)
    profile_image = Column(String)  # Path to the image
    hashed_password = Column(String)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(String, index=True)
    session_title = Column(String, nullable=True)  # Custom title
    role = Column(String)
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    tokens_used = Column(Integer, nullable=True)
    model_used = Column(String, nullable=True)
    attachment_url = Column(String, nullable=True)


def migrate_database():
    """Auto-migrate: add missing columns to existing tables"""
    from sqlalchemy import text
    
    inspector = inspect(engine)
    
    # Get existing columns for users table
    if inspector.has_table("users"):
        user_columns = [col['name'] for col in inspector.get_columns("users")]
        
        with engine.connect() as conn:
            if "is_admin" not in user_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0"))
                conn.commit()
            if "created_at" not in user_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN created_at DATETIME"))
                conn.execute(text("UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))
                conn.commit()
            if "last_login" not in user_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN last_login DATETIME"))
                conn.commit()
    
    # Get existing columns for chat_history table
    if inspector.has_table("chat_history"):
        chat_columns = [col['name'] for col in inspector.get_columns("chat_history")]
        
        with engine.connect() as conn:
            if "tokens_used" not in chat_columns:
                conn.execute(text("ALTER TABLE chat_history ADD COLUMN tokens_used INTEGER"))
                conn.commit()
            if "model_used" not in chat_columns:
                conn.execute(text("ALTER TABLE chat_history ADD COLUMN model_used VARCHAR"))
                conn.commit()
            if "attachment_url" not in chat_columns:
                conn.execute(text("ALTER TABLE chat_history ADD COLUMN attachment_url VARCHAR"))
                conn.commit()


# Create tables and run migrations
Base.metadata.create_all(bind=engine)
migrate_database()
