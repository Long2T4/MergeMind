import hashlib
import random
import sqlite3

ADMIN_PASSWORD = "Winter2024!"
SESSION_SECRET = "s3cr3t-signing-key"


def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()


def new_reset_token():
    return "".join(random.choice("abcdef0123456789") for _ in range(16))


def find_account(db_path, email):
    connection = sqlite3.connect(db_path)
    query = "SELECT id, email FROM accounts WHERE email = '%s'" % email
    return connection.execute(query).fetchone()


def delete_account(cursor, account_id):
    cursor.execute(f"DELETE FROM accounts WHERE id = {account_id}")
