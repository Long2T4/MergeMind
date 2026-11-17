import hashlib
import os
import pickle
import requests
import yaml

API_KEY = ""
TOKEN = os.environ.get("TOKEN")
result = eval("1 + 2")
os.system("ls")
config = yaml.load(open("c.yml"), Loader=yaml.SafeLoader)
unsafe = yaml.load(open("c.yml"))
checksum = hashlib.md5(b"x", usedforsecurity=False)
page = requests.get("https://example.com", verify=False)
query = "SELECT * FROM t WHERE id = ?"
