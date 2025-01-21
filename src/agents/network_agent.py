from __future__ import annotations

import json
from typing import Any, List, Optional

import pandas as pd
from aioxmpp import JID
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from spade.template import Template

from src.agents.common_behaviours.subscribeable_behaviour import (
    MailingList,
    SubscriptionBehaviour,
)
from src.agents.common_behaviours.time_keeping_mixin import TimeKeepingMixin
from src.utils.csv_utils import save_updates_to_csv
from src.utils.logger import LoggerFactory

from .component_agent import ComponentAgent


class NetworkAgent(TimeKeepingMixin, ComponentAgent):
    # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        jid: str,
        password: str = "password",
        logger_factory: Optional[LoggerFactory] = None,
        log_threshold: Optional[int] = None,
        parent: Optional[JID] = None,
    ):
        super().__init__(
            jid, password, logger_factory=logger_factory, log_threshold=log_threshold
        )
        if parent is not None:
            self.parent = parent
        self._children: dict[JID, float] = {}
        self._power_updates: List[float] = []
        self.current_congestion: float = 0.0

        register_child_template = Template(metadata={"type": "register_child"})
        self.add_behaviour(RegistrationReceiveBehaviour(), register_child_template)

        power_update_template = Template(metadata={"type": "power_update"})
        self.add_behaviour(PowerUpdateReceiveBehaviour(), power_update_template)

        self.time_subscription_behaviour = SubscriptionBehaviour(
            {
                **self.time_subscription(self.jid.domain),
            }
        )
        self.add_behaviour(self.time_subscription_behaviour)

        self.queues["congestion"] = MailingList(
            subscribers=[], message_func=self._get_congestion_message
        )

    @property
    def children(self) -> List[JID]:
        return list(self._children.keys())

    @property
    def net_power_usage_kw(self) -> float:
        """Return the current net power usage of the component. A negative value means that this component is producing power."""
        return sum(self._children.values())

    def save_power_update(self, datetimestamp: str, value: float) -> None:
        self._power_updates.append(
            {"datetimestamp": datetimestamp, "Power Usage (kW)": value}
        )

    def show_end_result(self) -> None:
        if not self._power_updates:
            self.print("No power updates received.")
            return

        total_power = sum(update["Power Usage (kW)"] for update in self._power_updates)
        average_power = total_power / len(self._power_updates)
        highest_power = max(
            update["Power Usage (kW)"] for update in self._power_updates
        )
        lowest_power = min(update["Power Usage (kW)"] for update in self._power_updates)

        save_updates_to_csv("power_updates", self._power_updates)
        # ANSI escape codes for color
        HEADER_COLOR = "\033[1;36m"  # Cyan
        AVERAGE_COLOR = "\033[1;32m"  # Green
        LOWEST_COLOR = "\033[1;33m"  # Yellow
        HIGHEST_COLOR = "\033[1;31m"  # Red
        RESET_COLOR = "\033[0m"  # Reset to default

        # Creating the table
        header = f"{HEADER_COLOR}Description{' ' * 14}{'Power Usage'}{RESET_COLOR}"
        average_row = f"{AVERAGE_COLOR}Average Power Usage{RESET_COLOR}{' ' * (25 - len('Average Power Usage'))}{self.format_num(average_power)} kW"
        highest_row = f"{HIGHEST_COLOR}Highest Power Usage{RESET_COLOR}{' ' * (25 - len('Highest Power Usage'))}{self.format_num(highest_power)} kW"
        lowest_row = f"{LOWEST_COLOR}Lowest Power Usage{RESET_COLOR}{' ' * (25 - len('Lowest Power Usage'))}{self.format_num(lowest_power)} kW"

        # Printing the table
        print(header)
        print(average_row)
        print(highest_row)
        print(lowest_row)

    def _get_congestion_message(self, message: Message = Message()) -> Message:
        """
        Populate the message that subscribers receive with congestion data.

        This method gets called when one or more subscribers need to get the
        current congestion data as a message. A message is passed or created
        and can be modified based on what data subscribers need to receive.

        Args:
            message (Message): the message to populate.

        Returns:
            Message: the populated message.
        """
        message.body = json.dumps(
            {
                "congestion": {
                    "unit": "kW",
                    "value": self.current_congestion,
                },
            },
            default=str,
        )
        message.set_metadata("type", "congestion")
        return message


class RegistrationReceiveBehaviour(CyclicBehaviour):  # type: ignore
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.agent: NetworkAgent

    async def run(self) -> None:
        msg = await self.receive(timeout=0.1)

        if msg:
            # self.agent.print(f"Registering child {msg.sender}")
            self.agent._children[msg.sender] = 0.0


class PowerUpdateReceiveBehaviour(CyclicBehaviour):  # type: ignore
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.agent: NetworkAgent

    async def run(self) -> None:
        msg = await self.receive(timeout=0.1)

        if msg:
            body = json.loads(msg.body)
            self.agent._children[msg.sender] = body["value"]
            if body["value"] > 0:
                self.agent.print(
                    f"Received power update from {msg.sender}: {self.agent.format_num(body['value'])} kW"
                )
            if self.agent.parent is None:
                self.agent.current_congestion = self.agent.net_power_usage_kw
                self.agent.save_power_update(
                    self.agent.get_formatted_sim_timestamp(),
                    self.agent.net_power_usage_kw,
                )
                if self.agent.net_power_usage_kw > 0:
                    color = "\033[91m"  # Red
                elif self.agent.net_power_usage_kw < 0:
                    color = "\033[93m"  # Orange
                else:
                    color = "\033[92m"  # Green
                self.agent.print(
                    f"{color}Total power usage @{self.agent.get_formatted_sim_timestamp()}: {self.agent.format_num(self.agent.net_power_usage_kw)} kW\033[0m"
                )
                await self.agent.send_update("congestion")
            self.agent.send_power_update_to_parent()
