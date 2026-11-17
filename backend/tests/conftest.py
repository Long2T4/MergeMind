"""Shared test setup.

Stage 13: tests don't depend on which scanners happen to be installed (CI's
Ubuntu job has Semgrep and Bandit; a Windows machine may have neither).
Unless a test is marked `real_scanners`, both scanners report "not
installed", just as the AI and GitHub are faked in tests. Tests that patch
the scanners themselves still work: their patches apply on top of this.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest

from app.services import analysis_service
from app.services.bandit_service import BanditUnavailable
from app.services.semgrep_service import SemgrepUnavailable


def pytest_configure(config):
    config.addinivalue_line("markers", "real_scanners: run the installed Semgrep and Bandit")


@pytest.fixture(autouse=True)
def _scanners_not_installed(request, monkeypatch):
    if request.node.get_closest_marker("real_scanners"):
        return

    def semgrep_missing(*args, **kwargs):
        raise SemgrepUnavailable("Semgrep is stubbed out in tests")

    def bandit_missing(*args, **kwargs):
        raise BanditUnavailable("Bandit is stubbed out in tests")

    monkeypatch.setattr(analysis_service, "run_semgrep_scan", semgrep_missing)
    monkeypatch.setattr(analysis_service, "run_bandit_scan", bandit_missing)
