"""Spins up a REAL backend process (not FastAPI's in-process TestClient) for
genuinely independent QA verification -- concurrency and rate-limit/lockout
threshold behavior in particular depend on real process/thread scheduling and
real wall-clock timing that an in-process TestClient sidesteps. Each test
module that needs a distinct configuration (e.g. a low rate limit) starts its
own disposable instance; nothing here is shared with app/tests/ (the
backend's own suite), by design -- this is the independent Test stage, not a
rerun of the implementer's own tests.
"""
from __future__ import annotations

import contextlib
import os
import shutil
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass

import httpx

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_PYTHON = os.path.join(REPO_ROOT, ".venv", "bin", "python3")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@dataclass
class RunningServer:
    base_url: str
    process: subprocess.Popen
    data_dir: str

    def stop(self) -> None:
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)
        shutil.rmtree(self.data_dir, ignore_errors=True)


def start_server(env_overrides: dict[str, str] | None = None, timeout_seconds: float = 10.0) -> RunningServer:
    port = _free_port()
    data_dir = tempfile.mkdtemp(prefix="qa-backend-")
    env = {
        **os.environ,
        "DATABASE_PATH": os.path.join(data_dir, "test.db"),
        "CHROMA_PERSIST_DIR": os.path.join(data_dir, "chroma"),
        "SHARED_USERNAME": "qa-user",
        "SHARED_PASSWORD": "qa-password-for-independent-testing",
        "SESSION_SECRET_KEY": "qa-suite-only",
        "NLU_ENGINE": "rule_based",
        "RATE_LIMIT_PER_MINUTE": "1000",
        "LOGIN_LOCKOUT_ATTEMPTS": "100",
        "LOGIN_LOCKOUT_WINDOW_MINUTES": "15",
        "DUE_SOON_WINDOW_DAYS": "7",
        **(env_overrides or {}),
    }
    process = subprocess.Popen(
        [VENV_PYTHON, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    base_url = f"http://127.0.0.1:{port}"
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        if process.poll() is not None:
            output = process.stdout.read().decode("utf-8", errors="replace") if process.stdout else ""
            raise RuntimeError(f"backend process exited early (code {process.returncode}):\n{output}")
        try:
            resp = httpx.get(f"{base_url}/health", timeout=1.0)
            if resp.status_code == 200:
                return RunningServer(base_url=base_url, process=process, data_dir=data_dir)
        except httpx.HTTPError as exc:
            last_error = exc
        time.sleep(0.2)
    process.kill()
    shutil.rmtree(data_dir, ignore_errors=True)
    raise RuntimeError(f"backend did not become healthy within {timeout_seconds}s: {last_error}")


@contextlib.contextmanager
def running_server(env_overrides: dict[str, str] | None = None):
    server = start_server(env_overrides)
    try:
        yield server
    finally:
        server.stop()
