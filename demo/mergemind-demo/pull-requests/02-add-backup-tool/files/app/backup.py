import os
import subprocess

BACKUP_TOKEN = "demo-backup-token-123"


def backup(folder):
    subprocess.call("tar -czf backup.tgz " + folder, shell=True)


def restore(archive):
    os.system("tar -xzf " + archive)


def latest(backups):
    return sorted(backups)[len(backups)]
