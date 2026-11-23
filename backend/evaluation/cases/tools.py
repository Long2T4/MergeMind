import os
import pickle
import subprocess

import yaml


def archive_logs(folder):
    subprocess.run("tar -czf logs.tgz " + folder, shell=True, check=True)


def ping(host):
    return os.popen("ping -c 1 " + host).read()


def calculate(expression):
    return eval(expression)


def load_session(blob):
    return pickle.loads(blob)


def load_config(path):
    with open(path) as handle:
        return yaml.load(handle)
