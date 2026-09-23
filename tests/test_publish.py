import json
import subprocess

from pipeline import publish


def _valid_output(path):
    (path / "metrics.json").write_text(
        json.dumps({"passed": True, "rows_published": 12}), encoding="utf-8"
    )


def _set_credentials(monkeypatch):
    monkeypatch.setenv("KAGGLE_USERNAME", "test-user")
    monkeypatch.setenv("KAGGLE_KEY", "test-key")


def test_create_mode_skips_status_lookup(tmp_path, monkeypatch):
    _valid_output(tmp_path)
    _set_credentials(monkeypatch)
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(publish.subprocess, "run", fake_run)

    publish.publish(tmp_path, "test-user/test-dataset", public=True, create=True)

    assert calls == [["kaggle", "datasets", "create", "-p", str(tmp_path), "-u"]]


def test_auto_mode_versions_existing_dataset(tmp_path, monkeypatch):
    _valid_output(tmp_path)
    _set_credentials(monkeypatch)
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(publish.subprocess, "run", fake_run)

    publish.publish(tmp_path, "test-user/test-dataset")

    assert calls[0] == ["kaggle", "datasets", "status", "test-user/test-dataset"]
    assert calls[1][:4] == ["kaggle", "datasets", "version", "-p"]
