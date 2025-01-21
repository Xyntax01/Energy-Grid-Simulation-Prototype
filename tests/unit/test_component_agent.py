from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio

from src.agents.component_agent import ComponentAgent


@pytest_asyncio.fixture(name="mock_component")
def _fixture_mock_component_agent() -> ComponentAgent:
    """Create a mocked SendPowerUpdateBehaviour."""
    agent = ComponentAgent(jid="test@test", password="test")
    agent._running = True
    return agent


@pytest.mark.asyncio
@patch("src.agents.simple_agent.SimpleAgent.stop")
@patch("src.agents.component_agent.ComponentAgent.send_power_update_to_parent")
async def test_stop(
    power_update_mock: Mock, stop_mock: AsyncMock, mock_component: ComponentAgent
) -> None:
    await mock_component.stop()

    assert not mock_component.running
    power_update_mock.assert_called_once()
    stop_mock.assert_called_once()
