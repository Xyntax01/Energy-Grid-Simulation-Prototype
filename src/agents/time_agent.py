import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

from spade.behaviour import CyclicBehaviour
from spade.message import Message

from src.agents.common_behaviours.subscribeable_behaviour import MailingList
from src.agents.common_behaviours.time_keeping_mixin import TimeKeepingMixin
from src.agents.simple_agent import SimpleAgent
from src.utils.logger import LoggerFactory
from src.utils.service_jids import get_time_agent_jid


class TimeAgent(
    TimeKeepingMixin, SimpleAgent
):  # pylint: disable=too-many-instance-attributes
    """
    TimeAgent is the owner of the concept of simulation time. It calculates
    what time it is in the simulation and responds to requests to change the
    current simulation speed.
    """

    def __init__(
        self,
        domain: str,
        start_sim_timestamp: datetime,
        end_sim_timestamp: datetime,
        rate: float,
        password: str = "password",
        logger_factory: Optional[LoggerFactory] = None,
        log_threshold: Optional[int] = None,
    ) -> None:
        """
        Initialize the Time Agent.

        Args:
            domain (str): the domain to use for message passing
            start_sim_timestamp (datetime): A timestamp denoting the start time
                for the simulation
            rate (float): the speed at which the simulation runs compared to
                realtime. E.g. 1.0 means realtime, 2.0 means twice as fast, 0.5
                means half as fast.
        """
        jid = get_time_agent_jid(domain)
        super().__init__(
            jid=jid,
            password=password,
            logger_factory=logger_factory,
            log_threshold=log_threshold,
        )
        self._real_broadcast_timestamp: datetime = datetime.now(timezone.utc)
        self._sim_broadcast_timestamp: datetime = start_sim_timestamp
        self._sim_end_timestamp: datetime = end_sim_timestamp
        self._rate = rate
        self.original_rate = rate
        self.rate_change_behaviour = RateChangeBehaviour()
        self.queues["time"] = MailingList(
            subscribers=[], message_func=self._get_time_message
        )

    async def setup(self) -> None:
        """
        Configure the agent.
        """
        await super().setup()
        self.print(
            f"starting simulation at {self._sim_broadcast_timestamp} with rate {self._rate}"
        )
        self.add_behaviour(self.rate_change_behaviour)
        self.pause_simulation()

    def _get_time_message(self, message: Message = Message()) -> Message:
        """
        Populate the message that subscribers receive with (meta)data.

        This method gets called when one or more subscribers need to get the
        current data as a message. A message is passed or created and can be
        modified based on what data subscribers need to receive.

        Args:
            message (Message): the message to populate.

        Returns:
            Message: the populated message.
        """
        message.body = json.dumps(
            {
                "real_broadcast_time": {
                    "unit": "ISO datetime",
                    "value": datetime.now(timezone.utc).isoformat(),
                },
                "sim_broadcast_time": {
                    "unit": "ISO datetime",
                    "value": self._sim_broadcast_timestamp.isoformat(),
                },
                "rate": {
                    "unit": "factor (no unit)",
                    "value": self.rate,
                },
            },
            default=str,
        )
        message.set_metadata("type", "time")
        return message

    @TimeKeepingMixin.rate.setter  # type: ignore
    def rate(self, new_rate: float) -> None:
        """
        Update to the new simulation rate and send out a broadcast to subscribers.
        Args:
            new_rate (float): the rate at which the simulation will run on from
                now on.
        """
        TimeKeepingMixin.rate.fset(self, new_rate)  # type: ignore
        asyncio.create_task(self.send_update())

    def update_broadcast_timestamps(self) -> None:
        """
        Update the real and simulated broadcast attributes for the time agent.
        """
        self.real_broadcast_timestamp = datetime.now(timezone.utc)
        self.sim_broadcast_timestamp = self.sim_timestamp

    async def send_update(self, queue: str = "time") -> None:
        """
        Update the broadcast attributes and send out the update to subscribers

        Args:
            queue (str: "time): the type of messages to subscribe to
        """
        if queue == "time":
            self.update_broadcast_timestamps()
        await super().send_update(queue)

    def end_simulation(self) -> bool:
        """
        End the simulation and send out the last update to subscribers.
        """
        # self.print("Ending simulation at", self.sim_timestamp, self._sim_end_timestamp)
        return self.sim_timestamp >= self._sim_end_timestamp

    def pause_simulation(self) -> None:
        """
        Pause the simulation by setting the rate to 0.
        """
        self.rate = 0.0

    async def resume_simulation(self) -> None:
        """
        Resume the simulation by setting the rate to 1.
        """
        self.print(f"Resuming simulation {self.original_rate}")
        self.update_broadcast_timestamps()
        await asyncio.sleep(1)
        self.rate = self.original_rate


class RateChangeBehaviour(CyclicBehaviour):  # type: ignore
    """Behaviour that generates and keeps time parameters to be sent to subscribers."""

    def __init__(self) -> None:
        """Initialize the behaviour."""
        super().__init__()
        self.agent: TimeAgent

    async def run(self) -> None:
        """
        Listen for `rateChange` messages. When a rate change has been received,
        update the rate of the time agent
        """
        msg = await self.receive(timeout=0.1)

        if msg is not None and msg.metadata["type"] == "rateChange":
            data = json.loads(msg.body)
            new_rate = float(data["rate"]["value"])
            self.agent.rate = new_rate
