import os
import subprocess


def get_password():
    return os.environ["DB_PASSWORD"]


def run(args):
    return subprocess.run(["git", *args], check=True, capture_output=True)


def average(values):
    return sum(values) / len(values) if values else 0
