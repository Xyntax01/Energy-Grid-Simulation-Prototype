from abc import ABC
from typing import List, Optional

from aioxmpp import JID

from src.agents.component_agent import ComponentAgent
from src.enums.component_types import ComponentType
from src.utils.csv_utils import save_updates_to_csv
from src.utils.logger import LoggerFactory


class BaseProsumptionAgent(ComponentAgent, ABC):
    """
    Base class for every asset (consumer/producer) that can exist in a network.
    """

    def __init__(
        self,
        jid: str,
        asset_type: Optional[str] = None,
        component_type: Optional[ComponentType] = None,
        max_power_usage_kw: Optional[float] = None,
        password: str = "password",
        parent: Optional[JID] = None,
        logger_factory: Optional[LoggerFactory] = None,
        log_threshold: Optional[int] = None,
    ):
        if not isinstance(component_type, ComponentType):
            raise ValueError(
                f"component_type must be a valid ComponentType, {component_type} given"
            )

        super().__init__(
            jid, password, logger_factory=logger_factory, log_threshold=log_threshold
        )
        self.type = component_type
        self.asset_type = asset_type
        self._power_updates: List[float] = []
        if max_power_usage_kw:
            self._max_power_usage_kw = max_power_usage_kw
        else:
            raise ValueError("max_power_usage_kw must be provided")
        if parent:
            self.parent = parent

    async def setup(self) -> None:
        """Configure the agent."""
        await super().setup()

    def on_unavailable_handler(self) -> None:
        save_updates_to_csv(f"{self.asset_type}_power_usage", self._power_updates)

    def save_power_update(self, datetimestamp: str, value: float) -> None:
        self._power_updates.append(
            {
                "datetimestamp": datetimestamp,
                "jid": self.jid.localpart,
                "Power Usage (kW)": round(value, 4),
            }
        )

    @property
    def max_power_usage_kw(self) -> float:
        """Returns the maximum power usage of the component."""
        return self._max_power_usage_kw

    @property
    def status(self) -> str:
        """A short, textual description of the current state of the device.

        Returns:
            str: The description
        """
        return "undefined"
