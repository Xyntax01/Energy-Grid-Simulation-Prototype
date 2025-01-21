from datetime import datetime, timezone
from typing import Any, Callable, Dict, List

from spade.behaviour import CyclicBehaviour, PeriodicBehaviour

from src.utils.service_jids import get_time_agent_jid


class TimeKeepingMixin:
    """
    Agent add-on that handles updating time variables and calculating the simulated time
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the agent.
        """
        super().__init__(*args, **kwargs)
        self._real_broadcast_timestamp: datetime = datetime.now(timezone.utc)
        self._sim_broadcast_timestamp: datetime = self._real_broadcast_timestamp
        self._rate: float = 1.0
        if not hasattr(self, "behaviours"):
            self.behaviours: List[CyclicBehaviour] = []

    def process_time_message(self, data: Dict[str, Any]) -> None:
        self.real_broadcast_timestamp = data["real_broadcast_time"]["value"]
        self.sim_broadcast_timestamp = data["sim_broadcast_time"]["value"]
        self.rate = data["rate"]["value"]

    def time_subscription(
        self, domain: str
    ) -> Dict[str, Dict[str, Callable[[Dict[str, Any]], None]]]:
        """
        Returns a subscription dictionary with the time agent jid, its queue and the time message handling function.

        Args:
            domain (str): the domain to use for message passing
        """
        return {
            get_time_agent_jid(domain): {
                "time": self.process_time_message,
            }
        }

    @property
    def real_broadcast_timestamp(self) -> datetime:
        """Returns the real broadcast time"""
        return self._real_broadcast_timestamp

    @real_broadcast_timestamp.setter
    def real_broadcast_timestamp(self, new_timestamp: datetime | str) -> None:
        """Sets the real broadcast time"""
        self._real_broadcast_timestamp = self._to_datetime(new_timestamp)

    @property
    def sim_broadcast_timestamp(self) -> datetime:
        """Returns the simulated broadcast time"""
        return self._sim_broadcast_timestamp

    @sim_broadcast_timestamp.setter
    def sim_broadcast_timestamp(self, new_timestamp: datetime | str) -> None:
        """Sets the simulated broadcast time"""
        self._sim_broadcast_timestamp = self._to_datetime(new_timestamp)

    @property
    def sim_timestamp(self) -> datetime:
        """Calculates the current simulated time"""
        real_timestamp = datetime.now(timezone.utc)
        time_difference = real_timestamp - self.real_broadcast_timestamp
        sim_timestamp = self.sim_broadcast_timestamp + (self.rate * time_difference)
        return sim_timestamp

    def get_formatted_sim_timestamp(self) -> str:
        """Returns the formatted simulated timestamp"""
        return self.sim_timestamp.strftime("%d-%m-%Y %H:%M:%S")

    @property
    def rate(self) -> float:
        """Returns the time rate"""
        return self._rate

    @rate.setter
    def rate(self, new_rate: float) -> None:
        """Sets the time rate and updates the period of the agent's periodic behaviours"""
        previous_rate = self._rate
        self._rate = new_rate
        for behaviour in self.behaviours:
            if isinstance(behaviour, PeriodicBehaviour):
                original_period = previous_rate * behaviour.period.total_seconds()
                if self._rate == 0:
                    behaviour.period = original_period
                else:
                    behaviour.period = original_period / self._rate

    def _to_datetime(self, timestamp: Any) -> datetime:
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except ValueError as exc:
                raise ValueError(
                    "timestamp must be a datetime object or a string in ISO format, given string could not be parsed."
                ) from exc

        if not isinstance(timestamp, datetime):
            raise TypeError(
                f"timestamp must be a datetime object or a string in ISO format, given {type(timestamp)}"
            )

        return timestamp
