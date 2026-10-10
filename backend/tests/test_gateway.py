import stat

from app import qloo_gateway


def fake_qloo(tmp_path, monkeypatch, body):
    exe = tmp_path / "qloo"
    exe.write_text("#!/bin/sh\n" + body)
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("QLOO_BIN", str(exe))


def test_missing_harness_is_a_clear_error(monkeypatch):
    monkeypatch.setenv("QLOO_BIN", "/nonexistent/qloo")
    env = qloo_gateway.find_tags("jazz")
    assert env["status"] == "error" and env["error"]["code"] == "HARNESS_MISSING"
    assert qloo_gateway.mode()[0] == "mock"


def test_ok_envelope_passes_through(tmp_path, monkeypatch):
    fake_qloo(tmp_path, monkeypatch, """echo '{"status":"ok","summary":"s","results":[{"x":1}],"result_count":1}'\n""")
    env = qloo_gateway.find_tags("jazz")
    assert env["status"] == "ok" and env["result_count"] == 1


def test_garbage_output_becomes_error(tmp_path, monkeypatch):
    fake_qloo(tmp_path, monkeypatch, "echo not-json\n")
    assert qloo_gateway.find_tags("jazz")["error"]["code"] == "BAD_OUTPUT"


def test_harness_error_envelope_is_kept(tmp_path, monkeypatch):
    fake_qloo(tmp_path, monkeypatch, """echo '{"status":"error","summary":"bad key","results":[],"result_count":0,"error":{"code":"QLOO_AUTH","retryable":false,"recovery":"r"}}'\nexit 1\n""")
    assert qloo_gateway.find_tags("jazz")["error"]["code"] == "QLOO_AUTH"
