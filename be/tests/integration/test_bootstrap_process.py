"""Chạy backend như Tauri sẽ chạy: một dòng BootstrapConfig qua stdin, đọc `ready`, gọi health,
đóng stdin → tiến trình tự thoát (T01, F00 be.md §B/§D)."""

import json
import subprocess
import sys
import threading

import httpx

from writestory_be.bootstrap.protocol import BootstrapConfig


def _start(data_root, token="proc-token"):
    proc = subprocess.Popen(
        [sys.executable, "-m", "writestory_be"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    config = BootstrapConfig(protocol_version=1, token=token, data_root=data_root, data_id="p1")
    proc.stdin.write((config.model_dump_json() + "\n").encode())
    proc.stdin.flush()
    # Drain stderr để pipe không đầy làm treo tiến trình.
    threading.Thread(target=proc.stderr.read, daemon=True).start()
    return proc


def _read_message(proc, timeout=30) -> dict:
    result: dict = {}

    def _read():
        line = proc.stdout.readline()
        if line:
            result.update(json.loads(line))

    t = threading.Thread(target=_read, daemon=True)
    t.start()
    t.join(timeout)
    return result


def _wait_ready(proc) -> dict:
    while True:
        msg = _read_message(proc)
        if msg.get("event") != "progress":
            return msg


def test_ready_health_and_exit_on_stdin_eof(tmp_path):
    proc = _start(tmp_path / "data")
    try:
        ready = _wait_ready(proc)
        assert ready["event"] == "ready", ready
        port = ready["port"]
        resp = httpx.get(
            f"http://127.0.0.1:{port}/v1/health",
            headers={"Authorization": "Bearer proc-token"},
            timeout=5,
        )
        assert resp.status_code == 200
        assert resp.json()["data_id"] == "p1"

        proc.stdin.close()  # mô phỏng Rust chết/đóng pipe
        assert proc.wait(timeout=15) == 0
    finally:
        if proc.poll() is None:
            proc.kill()


def test_second_backend_on_same_data_root_is_rejected(tmp_path):
    first = _start(tmp_path / "data")
    try:
        assert _wait_ready(first)["event"] == "ready"
        second = _start(tmp_path / "data")
        try:
            msg = _wait_ready(second)
            assert msg == {
                "event": "fatal",
                "code": "DATA_ROOT_LOCKED",
                "message": msg["message"],
                "detail": {},
            }
            assert second.wait(timeout=15) == 4
        finally:
            if second.poll() is None:
                second.kill()
    finally:
        first.stdin.close()
        first.wait(timeout=15)
