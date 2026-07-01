"""Tests for core/xapi_client.py."""

import json
from unittest.mock import patch, MagicMock

import pytest

from breaker.core.schema import (
    Ritual,
    RitualResult,
    ActionType,
    EventType,
    XapiActor,
)
from breaker.core.xapi_client import (
    LrsConfig,
    build_statement,
    send_statement,
    send_statements_batch,
    _send_mock,
    _send_real,
)


@pytest.fixture
def success_result():
    ritual = Ritual(
        signal="файл пуст",
        action="написать функцию",
        target="example.py",
        action_type=ActionType.OPEN_FILE,
        task_id="task_123",
    )
    return RitualResult(
        ritual=ritual,
        success=True,
        evidence_link="file:///path/to/example.py",
    )


@pytest.fixture
def error_result():
    from breaker.core.schema import RitualResult
    
    ritual = Ritual(
        signal="файл не найден",
        action="проверить путь",
        target="missing.py",
        action_type=ActionType.OPEN_FILE,
        task_id="task_456",
    )
    result = RitualResult(
        ritual=ritual,
        success=False,
        error_message="File not found: missing.py",
    )
    result.mark_finished()
    return result

@pytest.fixture
def actor():
    return XapiActor(mbox="mailto:student@example.com", name="Student")


@pytest.fixture
def mock_config():
    return LrsConfig(url="http://test-lrs/xAPI", mode="mock")


@pytest.fixture
def real_config():
    return LrsConfig(
        url="http://test-lrs/xAPI",
        key="test_key",
        secret="test_secret",
        mode="real",
    )


class TestLrsConfig:
    def test_default_config(self):
        config = LrsConfig()
        assert config.url == "http://localhost:8080/xAPI"
        assert config.mode == "mock"
        assert config.is_mock is True

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("LRS_URL", "http://custom/xAPI")
        monkeypatch.setenv("LRS_KEY", "k")
        monkeypatch.setenv("LRS_SECRET", "s")
        monkeypatch.setenv("LRS_MODE", "real")

        config = LrsConfig.from_env()
        assert config.url == "http://custom/xAPI"
        assert config.key == "k"
        assert config.secret == "s"
        assert config.is_mock is False

    def test_is_mock_real_mode(self):
        config = LrsConfig(mode="real")
        assert config.is_mock is False

    def test_is_mock_case_insensitive(self):
        config = LrsConfig(mode="MOCK")
        assert config.is_mock is True


class TestBuildStatement:
    def test_build_with_defaults(self, success_result):
        statement = build_statement(success_result)
        data = statement.to_dict()
        assert "actor" in data
        assert data["verb"]["id"] == "http://adlnet.gov/expapi/verbs/launched"
        assert data["object"]["id"] == "task:task_123"

    def test_build_with_custom_actor(self, success_result, actor):
        statement = build_statement(success_result, actor=actor)
        data = statement.to_dict()
        assert data["actor"]["mbox"] == "mailto:student@example.com"

    def test_build_with_course_id(self, success_result, actor):
        statement = build_statement(success_result, actor=actor, course_id="CS101")
        data = statement.to_dict()
        assert data["context"]["contextActivities"]["parent"][0]["id"] == "course:CS101"

    def test_build_planned_event(self, success_result, actor):
        statement = build_statement(
            success_result,
            actor=actor,
            event_type=EventType.PLAN_CREATED,
        )
        data = statement.to_dict()
        assert data["verb"]["id"] == "http://adlnet.gov/expapi/verbs/planned"

    def test_statement_contains_if_then_rule(self, success_result, actor):
        statement = build_statement(success_result, actor=actor)
        data = statement.to_dict()
        extensions = data["result"]["extensions"]
        assert "ifThenRule" in extensions
        assert "ЕСЛИ" in data["result"]["response"]


class TestSendMock:
    def test_mock_prints_to_stdout(self, success_result, actor, capsys):
        statement = build_statement(success_result, actor=actor)
        result = _send_mock(statement)

        captured = capsys.readouterr()
        assert result is True
        assert "[MOCK]" in captured.out
        assert "task_123" in captured.out

    def test_mock_output_is_valid_json(self, success_result, actor, capsys):
        statement = build_statement(success_result, actor=actor)
        _send_mock(statement)

        captured = capsys.readouterr()
        json_part = captured.out.split(":\n", 1)[1]
        parsed = json.loads(json_part)
        assert parsed["object"]["id"] == "task:task_123"


class TestSendReal:
    def test_real_send_success(self, success_result, actor, real_config):
        statement = build_statement(success_result, actor=actor)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response) as mock_post:
            result = _send_real(statement, real_config)

            assert result is True
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args.args[0] == "http://test-lrs/xAPI/statements"
            assert call_args.kwargs["auth"] == ("test_key", "test_secret")
            assert call_args.kwargs["headers"]["X-Experience-API-Version"] == "1.0.3"
            assert call_args.kwargs["timeout"] == 10

    def test_real_send_network_error(self, success_result, actor, real_config, capsys):
        import requests

        statement = build_statement(success_result, actor=actor)

        with patch("requests.post", side_effect=requests.exceptions.ConnectionError("no network")):
            result = _send_real(statement, real_config)

            assert result is False
            captured = capsys.readouterr()
            assert "Failed" in captured.out

    def test_real_send_http_error(self, success_result, actor, real_config, capsys):
        import requests

        statement = build_statement(success_result, actor=actor)

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500")

        with patch("requests.post", return_value=mock_response):
            result = _send_real(statement, real_config)

            assert result is False
            captured = capsys.readouterr()
            assert "Failed" in captured.out

    def test_real_send_without_auth(self, success_result, actor):
        config = LrsConfig(url="http://test/xAPI", mode="real")
        statement = build_statement(success_result, actor=actor)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response) as mock_post:
            _send_real(statement, config)
            assert mock_post.call_args.kwargs["auth"] is None


class TestSendStatement:
    def test_send_mock_mode(self, success_result, mock_config, actor, capsys):
        result = send_statement(success_result, config=mock_config, actor=actor)

        assert result is True
        captured = capsys.readouterr()
        assert "[MOCK]" in captured.out

    def test_send_real_mode(self, success_result, real_config, actor):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response):
            result = send_statement(success_result, config=real_config, actor=actor)
            assert result is True

    def test_send_uses_env_config(self, success_result, monkeypatch, capsys):
        monkeypatch.setenv("LRS_MODE", "mock")
        monkeypatch.setenv("LRS_URL", "http://env-lrs/xAPI")

        result = send_statement(success_result)
        assert result is True

        captured = capsys.readouterr()
        assert "[MOCK]" in captured.out

    def test_send_with_error_result(self, error_result, mock_config, actor, capsys):
        result = send_statement(error_result, config=mock_config, actor=actor)

        assert result is True
        captured = capsys.readouterr()
        assert "File not found: missing.py" in captured.out


class TestSendStatementsBatch:
    def test_batch_all_success(self, success_result, mock_config, actor, capsys):
        results = [success_result, success_result, success_result]
        stats = send_statements_batch(results, config=mock_config, actor=actor)

        assert stats["sent"] == 3
        assert stats["failed"] == 0
        assert stats["total"] == 3

    def test_batch_with_failures(self, success_result, error_result, real_config, actor):
        results = [success_result, error_result, success_result]

        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            mock_resp = MagicMock()
            if call_count[0] == 2:
                import requests

                raise requests.exceptions.ConnectionError("fail")
            mock_resp.raise_for_status = MagicMock()
            return mock_resp

        with patch("requests.post", side_effect=side_effect):
            stats = send_statements_batch(results, config=real_config, actor=actor)

            assert stats["sent"] == 2
            assert stats["failed"] == 1
            assert stats["total"] == 3

    def test_batch_empty_list(self, mock_config, actor):
        stats = send_statements_batch([], config=mock_config, actor=actor)
        assert stats == {"sent": 0, "failed": 0, "total": 0}
