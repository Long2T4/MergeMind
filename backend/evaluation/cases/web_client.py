import os

import requests

UPLOAD_DIR = "/srv/uploads"


def fetch_profile(url):
    return requests.get(url, timeout=10, verify=False).json()


def fetch_preview(user_url):
    return requests.get(user_url, timeout=5).text


def read_upload(filename):
    with open(os.path.join(UPLOAD_DIR, filename)) as handle:
        return handle.read()
