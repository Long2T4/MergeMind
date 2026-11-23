import ast
import json
import subprocess

import yaml


def archive_logs(folder):
    subprocess.run(["tar", "-czf", "logs.tgz", folder], check=True)


def calculate(expression):
    return ast.literal_eval(expression)


def load_session(text):
    return json.loads(text)


def load_config(path):
    with open(path) as handle:
        return yaml.safe_load(handle)
