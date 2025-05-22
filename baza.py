import sqlite3
DB_NAME = "sqlite3.db"
conn = sqlite3.connect(DB_NAME)
c= conn.cursor()

c.execute('SELECT * FROM users')
x=c.fetchall()
print(x)

c.execute('SELECT * FROM clients')
x=c.fetchall()
print(x)

c.execute('SELECT * FROM restaurants')
x=c.fetchall()
print(x)

c.execute('SELECT * FROM waiters')
x=c.fetchall()
print(x)

c.execute('SELECT * FROM bookings')
x=c.fetchall()
print(x)

c.execute('SELECT * FROM reviews')
x=c.fetchall()
print(x)
