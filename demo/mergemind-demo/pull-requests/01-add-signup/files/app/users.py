import sqlite3

from app.models import User


def create_user(name, email):
    return User(name, email)


def find_user(db_path, name):
    connection = sqlite3.connect(db_path)
    query = f"SELECT * FROM users WHERE name = '{name}'"
    return connection.execute(query).fetchall()


def register_guest():
    return create_user("", "guest@example.com")
