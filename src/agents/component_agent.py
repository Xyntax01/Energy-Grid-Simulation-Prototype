from abc import abstractmethod
from typing import Optional

from aioxmpp import JID
from spade.behaviour import OneShotBehaviour
from spade.message import Message

from src.agents.common_behaviours.send_power_update_behaviour import (
    SendPowerUpdateBehaviour,
)
from src.agents.simple_agent import SimpleAgent


class ComponentAgent(SimpleAgent):
    _parent: Optional[JID] = None

    async def setup(self) -> None:
        await super().setup()
        self.send_power_update_to_parent()

    async def stop(self) -> None:
        """
        Send a power update to the parent when the agent is stopping
        """
        self._running = False
        self.send_power_update_to_parent()
        await super().stop()

    def send_power_update_to_parent(self) -> None:
        """Send a power update to the parent."""
        self.add_behaviour(SendPowerUpdateBehaviour())

    @property
    def parent(self) -> Optional[JID]:
        return self._parent

    @parent.setter
    def parent(self, parent: JID | str) -> None:
        if not isinstance(parent, JID | str):
            raise TypeError("Parent must be of type JID or str")

        if isinstance(parent, str):
            parent = JID.fromstr(parent)

        if not parent.localpart or not parent.domain:
            raise ValueError("Parent must be a valid JID with a localpart and domain")

        self._parent = parent
        self.add_behaviour(RegisterAtParentBehaviour())

    @property
    def domain(self) -> str:
        """Returns the domain of the component."""
        return str(self.jid.domain)

    @property
    @abstractmethod
    def net_power_usage_kw(self) -> float:
        """
        Returns the current net power usage of the component. A negative value means that this component is 'producing' power.
        """


class RegisterAtParentBehaviour(OneShotBehaviour):  # type: ignore
    def __init__(self) -> None:
        super().__init__()
        self.agent: ComponentAgent

    async def run(self) -> None:
        msg = Message(to=str(self.agent.parent), metadata={"type": "register_child"})
        await self.send(msg)
