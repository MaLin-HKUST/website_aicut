import sqlite3
conn = sqlite3.connect('/data/website_aicut.db')
conn.execute('CREATE TABLE test (id INTEGER)')
conn.commit()
conn.close()
print('sqlite3 OK')
