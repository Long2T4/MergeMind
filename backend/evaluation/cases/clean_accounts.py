import hashlib
import os
import secrets
import sqlite3

ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]
EMPTY_DEFAULT_TOKEN = ""


def hash_file(data):
    return hashlib.sha256(data).hexdigest()


def new_reset_token():
    return secrets.token_hex(16)


def find_account(db_path, email):
    connection = sqlite3.connect(db_path)
    return connection.execute("SELECT id, email FROM accounts WHERE email = ?", (email,)).fetchone()
