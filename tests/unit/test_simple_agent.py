import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from src.agents.simple_agent import PeriodicInfoUpdate, SimpleAgent


class DummyAgent(SimpleAgent):
    def __init__(self, var: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._var = var
        self._parent = "parent@localhost/235hnal"
        self._children = [
            "child1@localhost/12t2x",
            "child1@localhost/1245h",
            "child3@localhost",
        ]
        self._net_power_usage_kw = 12.12

    @property
    def var(self) -> str:
        return self._var

    @var.setter
    def var(self, value: str) -> None:
        self._var = value

    def vab(self) -> str:
        return "baz"

    @property
    def parent(self) -> str:
        return self._parent

    @property
    def children(self) -> list[str]:
        return self._children

    @property
    def net_power_usage_kw(self) -> float:
        return self._net_power_usage_kw


@pytest_asyncio.fixture(name="mock_agent")
async def _fixture_mock_agent() -> DummyAgent:
    """Create a mocked simple agent."""
    agent = DummyAgent(var="foo", jid="test@test", password="test")
    return agent


@pytest.mark.asyncio
@patch("src.agents.simple_agent.SimpleAgent.send_update")
@patch("spade.agent.Agent._async_start")
async def test_start(
    mock_async_start: AsyncMock, mock_send_update: AsyncMock, mock_agent: DummyAgent
) -> None:
    assert not mock_agent.running
    await mock_agent.start()

    mock_async_start.assert_called_once()
    mock_send_update.assert_called_once()
    assert mock_agent.running


@pytest.mark.asyncio
@patch("src.agents.simple_agent.SimpleAgent.send_update")
@patch("spade.agent.Agent._async_stop")
async def test_stop(
    mock_async_stop: AsyncMock, mock_send_update: AsyncMock, mock_agent: DummyAgent
) -> None:
    mock_agent._running = True
    await mock_agent.stop()

    mock_async_stop.assert_called_once()
    mock_send_update.assert_called_once()
    assert not mock_agent.running


def test_get_info_message(mock_agent: DummyAgent) -> None:
    message = mock_agent.get_info_message()
    message_body = json.loads(message.body)

    assert message_body.get("var") == "foo"
    assert message_body.get("vab") is None
    assert message_body.get("type") == "DummyAgent"
    assert not message_body.get("running")
    assert message_body.get("net_power_usage_kw") == 0
    assert not set(message_body.get("children")) ^ set(
        ["child1@localhost", "child3@localhost"]
    )
    assert message_body.get("parent") == "parent@localhost"


@patch("src.agents.simple_agent.SimpleAgent.send_update")
@patch("spade.agent.Agent._async_start")
@pytest.mark.asyncio
async def test_get_info_message_running(
    _: AsyncMock, __: AsyncMock, mock_agent: DummyAgent
) -> None:
    await mock_agent.start()
    message = mock_agent.get_info_message()
    message_body = json.loads(message.body)

    assert message_body.get("running")
    assert message_body.get("net_power_usage_kw") == 12.12


@pytest.mark.asyncio
async def test_format_num() -> None:
    agent = DummyAgent(var="foo", jid="test@test", password="test")
    number = 1.2345
    decimals = 3
    num = agent.format_num(number, decimals)

    assert isinstance(num, str)
    assert num == "1.234"


@pytest.mark.asyncio
@patch(
    "src.agents.common_behaviours.subscribeable_behaviour.PublishingAgentMixin.send_update"
)
async def test_send_update_not_called(
    mock_send_update: AsyncMock, mock_agent: DummyAgent
) -> None:
    behaviour = PeriodicInfoUpdate(1)
    behaviour.agent = mock_agent
    behaviour.last_info = mock_agent.get_info_message().body

    await behaviour.run()
    mock_send_update.assert_not_called()


@pytest.mark.asyncio
@patch("src.agents.simple_agent.SimpleAgent.send_update")
async def test_send_update_called(
    mock_send_update: AsyncMock, mock_agent: DummyAgent
) -> None:
    behaviour = PeriodicInfoUpdate(1)
    behaviour.agent = mock_agent
    behaviour.last_info = mock_agent.get_info_message().body
    mock_agent.var = "bar"

    await behaviour.run()
    mock_send_update.assert_called_once_with("info")
