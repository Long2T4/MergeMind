import hashlib
import os
import pickle
import subprocess

DB_PASSWORD = "hunter2"


def connect(user, password="admin123"):
    return f"{user}:{password}"


def calculate(expression):
    return eval(expression)


def run(command):
    subprocess.call(command, shell=True)


def run_os(command):
    os.system(command)


def load(blob):
    data = pickle.loads(blob)
    digest = hashlib.md5(blob).hexdigest()
    return data, digest


def find_user(cursor, name):
    cursor.execute("SELECT * FROM users WHERE name = '%s'" % name)


def safe(command_args):
    subprocess.run(command_args, check=True)


assert DB_PASSWORD, "missing"
