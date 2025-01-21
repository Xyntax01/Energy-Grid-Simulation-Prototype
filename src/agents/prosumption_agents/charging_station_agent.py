import asyncio
import random
from typing import Any, Dict, Optional

import json
from aioxmpp import JID
from spade.behaviour import CyclicBehaviour, OneShotBehaviour
from spade.message import Message

from src.agents.common_behaviours.subscribeable_behaviour import MailingList, SubscriptionBehaviour
from src.agents.common_behaviours.time_keeping_mixin import TimeKeepingMixin
from src.agents.prosumption_agents.base_prosumption_agent import BaseProsumptionAgent
from src.enums.component_types import ComponentType
from src.utils.csv_utils import save_updates_to_csv
from src.utils.logger import LoggerFactory
from src.utils.service_jids import get_main_network_agent_jid, get_cpo_agent_jid


class ChargingStationAgent(TimeKeepingMixin, BaseProsumptionAgent):
    """
    A power consuming component that charges electric vehicles.
    """

    # pylint: disable=too-many-instance-attributes
    def __init__(
        self,
        jid: str,
        asset_type: str,
        max_power_usage_kw: Optional[float] = None,
        factor: Optional[float] = 1.0,
        logger_factory: Optional[LoggerFactory] = None,
        log_threshold: Optional[int] = None,
        parent: Optional[JID] = None,
        ev_jid: Optional[str] = "",
        smart: bool = False,
        cpo: Optional[JID] = None,
    ):
        """
        Initialise the Charging station.
        """
        super().__init__(
            asset_type=asset_type,
            jid=jid,
            max_power_usage_kw=max_power_usage_kw,
            parent=parent,
            logger_factory=logger_factory,
            log_threshold=log_threshold,
            component_type=ComponentType.CONSUMER,
        )
        self._net_power_usage_kw = 0.0
        self._ev_jid = ev_jid
        self._secret_password = f"secretPassword-{self.jid.localpart}"
        self.is_charging = True
        self.smart = smart
        self.cpo = cpo
        self.factor = factor
        self.congestion = 0.0
        self.congestion_reduction_factor = 1.0
        self.behaviour = ChargingStationBehaviour()
        self.send_info_behaviour = ChargingStationSendInfoBehaviour()
        self.get_new_charge_speed_behaviour = ChargingStationCpoNewChargeSpeed()
        self.time_subscription_behaviour = SubscriptionBehaviour(
            {
                **self.time_subscription(self.jid.domain),
            }
        )
        self.congestion_subscription_behaviour = SubscriptionBehaviour(
            {
                get_main_network_agent_jid(self.jid.domain): {
                    "congestion": self._process_congestion_message,
                },
            }
        )
        self.start_time = self._get_random_start_time()
        self.stop_time = self._get_random_stop_time()

    def _get_random_start_time(self) -> int:
        """
        Get a random start time with a higher probability for times commonly used in real life.
        """
        common_times = [7, 8, 9, 17, 18, 19]
        if random.random() < 0.7:
            return random.choice(common_times)
        return random.randint(0, 23)

    def _get_random_stop_time(self) -> int:
        """
        Get a random stop time with a higher probability for times commonly used in real life.
        """
        common_charge_duration = [6,7,8]
        if random.random() < 0.8:
            return random.choice(common_charge_duration)
        duration = random.randint(1, 23)
        duration = max(1, min(duration, 23))  # Ensure duration is within the range 1-23
        endtime = self.start_time + duration
        if endtime > 23:
            endtime -= 24
        return endtime

    async def setup(self) -> None:
        await super().setup()

        self.add_behaviour(self.behaviour)
        self.add_behaviour(self.send_info_behaviour)
        self.add_behaviour(self.time_subscription_behaviour)
        self.add_behaviour(self.congestion_subscription_behaviour)
        if self.cpo:
            self.add_behaviour(self.get_new_charge_speed_behaviour)

    @property
    def net_power_usage_kw(self) -> float:
        """
        Returns the net power of this charging station. A negative value means that this station is returning power to the grid (V2G).
        """
        if self.is_charging:
            return self._net_power_usage_kw * self.factor
        return 0.0

    @property
    def ev_jid(self) -> Optional[str]:
        """
        Returns the localpart (JID) of the connected electric vehicle, returns empty string if no electric vehicle is connnected.
        """
        return self._ev_jid

    @property
    def status(self) -> str:
        if self.is_charging:
            return "charging"

        return "idle"

    def smart_charging(self) -> None:
        """
        Smart charging.
        """
        if self.congestion > 0.0:  # Overconsumption
            reduction_amount = self.congestion * self.congestion_reduction_factor  # Calculate reduction amount based on congestion
            self._net_power_usage_kw = max(0.001, self._net_power_usage_kw - reduction_amount)  # Ensure power usage doesn't go below 0
            self.print(f"Congestion: Overconsumption, Lowering charging speed to: {self._net_power_usage_kw}")
        elif self.congestion < 0.0:  # Oversupply
            reduction_factor = abs(self.congestion) / 100  # Calculate reduction factor based on congestion
            self._net_power_usage_kw += (1 - reduction_factor)  # Lower by calculated factor
            self._net_power_usage_kw = min(self._net_power_usage_kw, self.max_power_usage_kw)
            self.print(f"Congestion: Oversupply, Increasing charging speed to: {self._net_power_usage_kw}")
        else:  # No congestion
            self.print(f"Congestion: None, Maintaining charging speed: {self._net_power_usage_kw}")

    def _get_power_usage_message(self, message: Message = Message()) -> Message:
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
                "power_usage": {
                    "CS": self.jid.localpart,
                    "unit": "kW",
                    "value": self.net_power_usage_kw,
                    "is_charging": self.is_charging,
                },
            },
            default=str,
        )
        message.set_metadata("type", "cs_power_usage")
        return message
    
    def _process_congestion_message(self, data: Dict[str, Any]) -> None:
        self.congestion = float(data["congestion"]["value"])

class ChargingStationBehaviour(CyclicBehaviour):  # type: ignore
    def __init__(self) -> None:
        """
        Initialize the behaviour.

        """
        super().__init__()

        self.agent: ChargingStationAgent

    async def run(self) -> None:
        current_hour = self.agent.sim_timestamp.hour
        if self.agent.start_time >= current_hour < self.agent.stop_time:
            self.agent.is_charging = True
        else:
            self.agent.is_charging = False
        if self.agent.smart:
            if self.agent.cpo:
                message = self.agent._get_power_usage_message(message=Message(to=f"{self.agent.cpo}@{self.agent.jid.domain}"))
                await self.send(message)
            if self.agent.is_charging:
                if self.agent.cpo is None:
                    self.agent.smart_charging()

                self.agent.save_power_update(
                    self.agent.get_formatted_sim_timestamp(), self.agent._net_power_usage_kw
                )
                self.agent.print(
                    f"Charging station is charging {self.agent.is_charging} with {self.agent.net_power_usage_kw} kW"
                )
        else:
            if self.agent.is_charging:
                self.agent._net_power_usage_kw = self.agent.max_power_usage_kw
                self.agent.save_power_update(
                    self.agent.get_formatted_sim_timestamp(), self.agent._net_power_usage_kw
                )
                self.agent.print(
                    f"Charging station is charging {self.agent.is_charging} with {self.agent.net_power_usage_kw} kW"
                )       
        self.agent.send_power_update_to_parent()
        await asyncio.sleep(0.1)

class ChargingStationSendInfoBehaviour(OneShotBehaviour):  # type: ignore
    def __init__(self) -> None:
        """
        Initialize the behaviour.

        """
        super().__init__()

        self.agent: ChargingStationAgent

    async def run(self) -> None:
        msg = Message(to=f"cpo_1@{self.agent.jid.domain}")
        msg.thread = "cs-info"
        msg.body = f'{{"CS": "{self.agent.jid.localpart}"}}'

        await self.send(msg)
        # await asyncio.sleep(1)

class ChargingStationCpoNewChargeSpeed(CyclicBehaviour): # type: ignore
    def __init__(self) -> None:
        """
        Initialize the behaviour.

        """
        super().__init__()

        self.agent: ChargingStationAgent

    async def run(self) -> None:
        msg = await self.receive(timeout=0.1)

        if self.agent.is_charging and msg and msg.thread == "new-charging-speed":
            # self.agent.print(f"Received new charging speed: {msg.body}")
            msg_body = json.loads(msg.body)
            if "new_charging_speed" in msg_body:
                # self.agent.print("message about charging_speed: " + str(msg_body))
                new_power = msg_body["new_charging_speed"]
                if new_power > self.agent.max_power_usage_kw:
                    new_power = self.agent.max_power_usage_kw
                self.agent._net_power_usage_kw = new_power
        self.agent.send_power_update_to_parent()