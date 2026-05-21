from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "postgresql://postgres:admin@localhost:5432/cannabis_analysis"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


# DB Dependency
def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()