import asyncio
import json
from typing import Any, Dict, Optional

from spade.behaviour import CyclicBehaviour
from spade.message import Message

from src.agents.common_behaviours.subscribeable_behaviour import SubscriptionBehaviour
from src.agents.interaction_agents.base_interaction_agent import BaseInteractionAgent
from src.utils.logger import LoggerFactory
from src.utils.service_jids import get_main_network_agent_jid


class CpoAgent(BaseInteractionAgent):
    """
    A component that serves as a CPO.
    """

    def __init__(
        self,
        jid: str,
        password: str = "password",
        logger_factory: Optional[LoggerFactory] = None,
        log_threshold: Optional[int] = None,
    ):
        """
        Initialise CPO.
        """
        super().__init__(
            jid=jid,
            password=password,
            logger_factory=logger_factory,
            log_threshold=log_threshold,
        )
        self.charging_stations = []
        self.charging_stations_charge_speed = []
        self.charging_stations_new_charge_speed =[]
        self.congestion = 0.0
        self.behaviour = CpoBehaviour()
        self.receive_cs_info_behaviour = CpoReceiveCSInfoBehaviour()
        self.send_cs_new_charging_speed_behaviour = CpoSendCsNewChargingSpeed()

        self.congestion_subscription_behaviour = SubscriptionBehaviour(
            {
                get_main_network_agent_jid(self.jid.domain): {
                    "congestion": self._process_congestion_message,
                },
            }
        )

    async def setup(self) -> None:
        await super().setup()
        print(f"CPOAgent {self.jid} is running.")
        self.add_behaviour(self.behaviour)
        self.add_behaviour(self.receive_cs_info_behaviour)
        self.add_behaviour(self.congestion_subscription_behaviour)
        self.add_behaviour(self.send_cs_new_charging_speed_behaviour)

    async def smart_charging_css(self) -> None:
        await self.change_charging_speed()

    def _process_congestion_message(self, data: Dict[str, Any]) -> None:
        self.congestion = float(data["congestion"]["value"])
        # self.print(f"Received congestion: {self.congestion}")

    def calculate_average_charge_speed(self) -> None:
        if self.charging_stations_charge_speed:
            sum = 0
            count = self.charging_stations_charge_speed.__len__()
            for cs in self.charging_stations_charge_speed:
                for key, value in cs.items():
                    sum += value["value"]
            average = sum / count
            self.print(f"Average charge speed: {average}, {sum} {count} ")

    async def change_charging_speed(self) -> None:
        if not self.charging_stations_charge_speed:
            return  # No charging stations

        total_demand = sum(cs_data["value"] for cs in self.charging_stations_charge_speed for cs_data in cs.values())
        current_power = [list(cs.values())[0]["value"] for cs in self.charging_stations_charge_speed]
        if self.congestion > 0:
            self.print(f"Overconsumption: {self.congestion}")
            new_power = self.distribute_power_reduction(total_demand, self.congestion, current_power, reduction_factor=1)
        elif self.congestion < 0:
            self.print(f"Oversupply: {self.congestion}")
            num_charging_stations_charging = sum(1 for cs in self.charging_stations_charge_speed for cs_data in cs.values() if cs_data["is_charging"])
            new_power = self.distribute_power_increase(self.congestion, current_power, num_charging_stations_charging, increase_factor=1)

        for i, cs in enumerate(self.charging_stations_charge_speed):
            found = False
            cs_id = list(cs.keys())[0]  # Get the CS ID
            for cs in self.charging_stations_new_charge_speed:
                if cs_id in cs:
                    cs[cs_id] = new_power[i]
                    found = True
                    break
            if not found:
                self.charging_stations_new_charge_speed.append({cs_id: new_power[i]})

    def distribute_power_reduction(self, total_demand, congestion, current_power, reduction_factor=1.0):
        """Distributes power reduction proportionally."""
        if congestion <= 0 and total_demand <= 0:
            return current_power

        total_reduction = congestion * reduction_factor
        reduction_proportion = total_reduction / total_demand if total_demand != 0 else 0
        new_power = [max(0, power * (1 - reduction_proportion)) for power in current_power]
        return new_power

    def distribute_power_increase(self, congestion, current_power, num_charging_stations, increase_factor=1.0):
        """Distributes power increase proportionally."""

        # self.print(f"Congestion CPO data: {congestion} | {abs(congestion)} | {current_power} | {num_charging_stations}")
        if num_charging_stations > 0:
            increase_proportion = abs(congestion) / num_charging_stations * increase_factor
            self.print(f"Increase proportion: {increase_proportion}")
            new_power = [power + increase_proportion for power in current_power]
            # self.print(f"New power: {new_power}")
        else:
            new_power = current_power
        return new_power

class CpoBehaviour(CyclicBehaviour):  # type: ignore
    def __init__(self) -> None:
        """
        Initialize the behaviour.

        """
        super().__init__()

        self.agent: CpoAgent

    async def run(self) -> None:
        await self.agent.smart_charging_css()
        await asyncio.sleep(1)
        # self.agent.print("CPOBehaviour running")

class CpoReceiveCSInfoBehaviour(CyclicBehaviour):  # type: ignore
    def __init__(self) -> None:
        """
        Initialize the behaviour.

        """
        super().__init__()

        self.agent: CpoAgent

    async def run(self) -> None:
        msg = await self.receive()
        if msg:
            msg_body = json.loads(msg.body)
            if "CS" in msg_body:
                # self.agent.print(msg_body["CS"])
                self.agent.charging_stations.append(msg_body["CS"])
            elif "power_usage" in msg_body:
                # self.agent.print(msg_body["power_usage"])
                power_usage = msg_body["power_usage"]
                self.add_power_usage(power_usage["CS"], power_usage["unit"], power_usage["value"], power_usage["is_charging"])

    def add_power_usage(self, cs_id: str, unit: str, value: str, is_charging: bool) -> None:
        found = False
        for cs in self.agent.charging_stations_charge_speed:
            if cs_id in cs:
                cs[cs_id] = {"unit": unit, "value": value , "is_charging": is_charging}
                found = True
                break
        if not found:
            self.agent.charging_stations_charge_speed.append({cs_id: {"unit": unit, "value": value, "is_charging": is_charging}})

class CpoSendCsNewChargingSpeed(CyclicBehaviour): # type: ignore
    def __init__(self) -> None:
        """
        Initialize the behaviour.

        """
        super().__init__()

        self.agent: CpoAgent

    async def run(self) -> None:
        if self.agent.charging_stations_new_charge_speed:
            for cs in self.agent.charging_stations_new_charge_speed:
                for cs_id, power in cs.items():
                    message = Message(to=f"{cs_id}@{self.agent.jid.domain}")
                    message.thread = "new-charging-speed"
                    message.body = json.dumps({"new_charging_speed": power})
                    await self.send(message)
        await asyncio.sleep(0.1)