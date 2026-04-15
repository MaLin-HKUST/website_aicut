import sys
import os
sys.path.insert(0, "/app")
os.environ["DATABASE_URL"] = "sqlite:///data/website_aicut.db"
from app.database import engine, Base
from app.models import Company, User, AssetLibrary
print("Engine URL:", engine.url)
Base.metadata.create_all(bind=engine)
print("Tables created OK")
