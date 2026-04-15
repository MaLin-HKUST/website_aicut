import sys
sys.path.insert(0, "/app")
from app.models import Company, User, AssetLibrary
print("Models imported OK")
print("Company fields:", [c.name for c in Company.__table__.columns])
