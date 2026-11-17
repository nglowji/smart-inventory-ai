import json

import pytest

from app.core.config import Settings
from app.core.errors import DomainError
from app.modules.ai import check_connection as connection
from app.modules.ai.provider import ToolCall


def test_mock_mode_does_not_claim_live_connectivity():
    with pytest.raises(DomainError) as caught:
        connection.check_connection(Settings(_env_file=None, ai_provider="mock"))
    assert caught.value.code == "AI_TEST_MODE"


@pytest.mark.parametrize(
    "calls,valid",
    [
        ([ToolCall("list_low_stock", {"limit": 1})], True),
        ([], False),
        ([ToolCall("execute_sql", {})], False),
        ([ToolCall("list_low_stock", {"limit": 99})], False),
    ],
)
def test_check_validates_live_tool_call_without_querying_db(monkeypatch, calls, valid):
    class Provider:
        def plan(self, history, question):
            assert history == []
            return calls

    monkeypatch.setattr(connection, "configured_provider", lambda settings: Provider())
    settings = Settings(_env_file=None, ai_provider="openai")
    if valid:
        result = connection.check_connection(settings)
        assert result["ok"] is True
        assert result["code"] == "AI_CONNECTED"
    else:
        with pytest.raises(DomainError) as caught:
            connection.check_connection(settings)
        assert caught.value.code == "AI_TOOL_CALL_UNVERIFIED"


def test_cli_does_not_echo_invalid_configuration_secrets(monkeypatch, capsys):
    def invalid():
        return Settings(_env_file=None, ai_base_url="https://user:private-secret@example.com")

    monkeypatch.setattr(connection, "Settings", invalid)
    assert connection.main() == 2
    captured = capsys.readouterr().out
    assert json.loads(captured)["code"] == "AI_CONFIG_INVALID"
    assert "private-secret" not in captured


def test_cli_reports_missing_configuration_without_traceback(monkeypatch, capsys):
    monkeypatch.setattr(connection, "Settings", lambda: Settings(_env_file=None))
    assert connection.main() == 2
    assert json.loads(capsys.readouterr().out)["code"] == "AI_NOT_CONFIGURED"
