import pytest_asyncio

from src.agents.network_agent import NetworkAgent


@pytest_asyncio.fixture(name="mock_network_agent")
async def _fixture_mock_network_agent() -> NetworkAgent:
    """Create a mocked network agent."""
    agent = NetworkAgent(jid="test@test", password="test")
    return agent


def test_children(mock_network_agent: NetworkAgent) -> None:
    mock_network_agent._children = {"A": 1.234, "B": 2.345}
    assert mock_network_agent.children == ["A", "B"]


def test_net_power_usage(mock_network_agent: NetworkAgent) -> None:
    mock_network_agent._children = {"A": 1.234, "B": 2.345}
    assert mock_network_agent.net_power_usage_kw == 3.579
