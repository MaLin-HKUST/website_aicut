import sqlalchemy
print("SQLAlchemy version:", sqlalchemy.__version__)
from sqlalchemy import create_engine
engine = create_engine("sqlite:///data/test.db")
print("Engine created:", engine.url)
