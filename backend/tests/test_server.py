import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from megascans_browser.api.server import (
    DB_FILE_NAME,
    READY_PREFIX,
    bind_socket,
    parse_args,
    parse_ready_line,
    ready_line,
)


def test_parse_args_requires_the_user_data_path() -> None:
    with pytest.raises(SystemExit):
        parse_args([])


def test_parse_args_defaults_to_a_free_port() -> None:
    args = parse_args(["--user-data", "C:/tmp"])

    assert args.user_data == "C:/tmp"
    assert args.port == 0


def test_bind_socket_picks_a_free_port_on_loopback() -> None:
    listener = bind_socket("127.0.0.1", 0)
    try:
        host, port = listener.getsockname()
        assert host == "127.0.0.1"
        assert port > 0
    finally:
        listener.close()


def test_the_ready_line_round_trips() -> None:
    line = ready_line(50123, "a-token")

    assert line.startswith(READY_PREFIX)
    assert parse_ready_line(line) == {"port": 50123, "token": "a-token"}


def test_parse_ready_line_ignores_other_output() -> None:
    assert parse_ready_line("some uvicorn noise") is None


def read_ready(process: subprocess.Popen[str]) -> dict[str, object]:
    assert process.stdout is not None
    for _ in range(200):
        line = process.stdout.readline()
        if not line:
            break
        parsed = parse_ready_line(line.strip())
        if parsed is not None:
            return parsed
    raise AssertionError("起動の行が出てこなかった")


@pytest.mark.slow
def test_the_server_starts_and_answers_health(tmp_path: Path) -> None:
    process = subprocess.Popen(
        [sys.executable, "-m", "megascans_browser.api.server", "--user-data", str(tmp_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
    )
    try:
        ready = read_ready(process)
        port, token = ready["port"], ready["token"]

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=30) as response:
            assert json.loads(response.read())["status"] == "ok"

        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/settings", headers={"Authorization": f"Bearer {token}"}
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            assert json.loads(response.read())["configured"] is False

        with pytest.raises(urllib.error.HTTPError) as unauthorized:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/settings", timeout=30)
        assert unauthorized.value.code == 401

        assert (tmp_path / DB_FILE_NAME).is_file()
    finally:
        process.terminate()
        process.wait(timeout=30)
