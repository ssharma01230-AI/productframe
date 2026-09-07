import logging
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from productframe_worker import cli


@pytest.fixture
def command(monkeypatch):
    monkeypatch.setattr(cli, "load_dotenv", Mock())
    monkeypatch.setattr(cli, "get_settings", lambda: SimpleNamespace(redis_url="redis://test"))
    monkeypatch.setattr(cli.time, "sleep", Mock())
    # CLI startup sets library log levels; restore those levels after each test.
    for name in ("httpx", "httpcore", "urllib3", "openai", "botocore"):
        log = logging.getLogger(name)
        monkeypatch.setattr(log, "level", log.level)

    def select(name):
        monkeypatch.setattr(sys, "argv", ["productframe-worker", name])

    return select


@pytest.mark.parametrize("stop", [KeyboardInterrupt, SystemExit])
def test_worker_continues_after_failed_job_and_preserves_shutdown(command, monkeypatch, caplog, stop):
    command("run")
    failure = RuntimeError("sensitive-provider-response-and-credential")
    run_once = Mock(side_effect=[failure, True, stop()])
    monkeypatch.setattr(cli, "run_once", run_once)

    with caplog.at_level(logging.INFO, logger=cli.__name__):
        with pytest.raises(stop):
            cli.main()

    # One failed job must not prevent the next queued job from being processed.
    assert run_once.call_count == 3
    assert cli.time.sleep.call_count == 2
    errors = [record for record in caplog.records if record.name == cli.__name__ and record.levelno == logging.ERROR]
    assert len(errors) == 1
    assert "RuntimeError" in errors[0].getMessage()
    assert "continuing to listen" in errors[0].getMessage()
    assert "sensitive-provider-response-and-credential" not in caplog.text
    assert errors[0].exc_info is None


def test_run_once_still_propagates_job_failure(command, monkeypatch, caplog):
    command("run-once")
    failure = RuntimeError("Job failed")
    run_once = Mock(side_effect=failure)
    monkeypatch.setattr(cli, "run_once", run_once)

    with pytest.raises(RuntimeError) as caught:
        cli.main()

    assert caught.value is failure
    run_once.assert_called_once_with()
    cli.time.sleep.assert_not_called()
    assert not [record for record in caplog.records if record.name == cli.__name__]


def test_startup_keeps_analysis_metadata_visible_and_http_logs_quiet(command, monkeypatch, caplog):
    command("run-once")

    def run_once():
        logging.getLogger("productframe_api.analysis_router").info("analysis request provider=openai stage=ProductIdentity")
        logging.getLogger("httpx").info("HTTP transport details")
        logging.getLogger("httpcore").info("Connection transport details")
        return False

    monkeypatch.setattr(cli, "run_once", run_once)
    with caplog.at_level(logging.INFO):
        cli.main()

    assert "analysis request provider=openai stage=ProductIdentity" in caplog.text
    assert "HTTP transport details" not in caplog.text
    assert "Connection transport details" not in caplog.text
