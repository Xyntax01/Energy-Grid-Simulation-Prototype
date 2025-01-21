import json
from typing import TYPE_CHECKING

from spade.behaviour import OneShotBehaviour
from spade.message import Message

# Prevent circular imports
if TYPE_CHECKING:
    from src.agents.component_agent import ComponentAgent


class SendPowerUpdateBehaviour(OneShotBehaviour):  # type: ignore
    """Handle power update messages to the agent's parent."""

    def __init__(self) -> None:
        """Initialize the behaviour."""
        super().__init__()
        self.agent: "ComponentAgent"

    async def run(self) -> None:
        """Send a power update to the parent."""
        if not self.agent.parent:
            return

        if self.agent.running:
            power_usage = self.agent.net_power_usage_kw
        else:
            power_usage = 0

        msg = Message(
            to=str(self.agent.parent),
            body=json.dumps(
                {
                    "value": power_usage,
                    "unit": "kW",
                }
            ),
            metadata={"type": "power_update"},
        )
        await self.send(msg)
        # self.agent.print(
        #     f"Sent power update to {self.agent.parent} with value {self.agent.format_num(power_usage)} kW"
        # )
