from sqlmodel import create_engine, SQLModel
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

engine = create_engine(DATABASE_URL, echo=True)

def init_db():
    """Create the database tables."""
    SQLModel.metadata.create_all(engine)