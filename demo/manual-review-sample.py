import hashlib
import subprocess

API_KEY = "demo-key-123"


def run_report(name):
    subprocess.call("generate-report " + name, shell=True)


def checksum(data):
    return hashlib.md5(data).hexdigest()


def average(scores):
    return sum(scores) / len(scores)
