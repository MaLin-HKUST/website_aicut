import os
print('ENV:', os.environ.get('DATABASE_URL'))
from sqlalchemy import create_engine
engine = create_engine('sqlite:///data/website_aicut.db')
print('Engine:', engine.url)
conn = engine.connect()
print('Connected!')
conn.close()
