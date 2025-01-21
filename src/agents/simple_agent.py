import json
from datetime import datetime
from typing import Any, Optional

from spade.behaviour import PeriodicBehaviour
from spade.message import Message

from src.agents.common_behaviours.subscribeable_behaviour import (
    MailingList,
    PublishingAgentMixin,
)
from src.utils.logger import LoggerFactory


class SimpleAgent(PublishingAgentMixin):
    def __init__(
        self,
        *args: Any,
        logger_factory: Optional[LoggerFactory] = None,
        log_threshold: Optional[int] = None,
        period: float = 1,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        if logger_factory is None:
            logger_factory = LoggerFactory()
        self.logger = logger_factory.get_logger(self.name, log_threshold=log_threshold)
        self.queues["info"] = MailingList(
            subscribers=[],
            message_func=self.get_info_message,
        )
        self.info_behaviour = PeriodicInfoUpdate(period=period)
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    async def start(self, auto_register: bool = True) -> None:
        """
        Starts this agent.

        Args:
            auto_register (bool): register the agent in the server (Default value = True)
        """

        # self.print("Agent started running")
        self._running = True
        await self._async_start(auto_register=auto_register)
        await self.send_update("info")

    async def stop(self) -> None:
        """
        Stops this agent and sends a message to the API
        """

        # self.print("Agent stopped running")
        self._running = False
        await self.send_update("info")
        await self._async_stop()

    async def setup(self) -> None:
        await super().setup()
        self.add_behaviour(self.info_behaviour)

    def get_info_message(self, message: Message = Message()) -> Message:
        """
        Populates the body of a message with all instance attributes that are properties.
        Removes unwanted attributes: ["avatar"]
        Cleans up attributes: children: [(name, domain, null),] -> [(name),]

        Args:
            message (spade.message.Message): The message that will be populated.

        Returns:
            spade.message.Message: The populated message.
        """
        unwanted_attributes = ["avatar"]
        data: dict[str, Any] = {}
        data["type"] = type(self).__name__
        data["jid"] = str(self.jid)
        for obj in [self] + self.__class__.mro():
            for key, attr in obj.__dict__.items():
                if not key in unwanted_attributes:
                    if isinstance(attr, property):
                        attr_value = getattr(self, key)
                        if key == "children":
                            # List of strings in format 'localpart@domain/resource'
                            data[key] = list(
                                {
                                    str(child).split("/", maxsplit=1)[0]
                                    for child in attr_value
                                }
                            )
                        elif key == "parent":
                            # String in format 'localpart@domain/resource'
                            data[key] = (
                                str(attr_value).split("/", maxsplit=1)[0]
                                if attr_value is not None
                                else None
                            )
                        elif key == "net_power_usage_kw":
                            data[key] = attr_value if self.running else 0
                        else:
                            data[key] = attr_value
        message.body = str(json.dumps(data, default=str))
        message.set_metadata("type", "info")
        return message

    def print(self, *args: Any) -> None:
        """
        Prints a message with the name of the component prefixed.

        Args:
            *args: positional arguments to be passed to the print function.
        """
        self.logger.info(*args)

    def format_num(self, number: float | int, decimals: int = 3) -> str:
        """
        String representation of a number which always cuts off at and fills to
        `decimals` decimal places.

        Args:
            number (float | int): the number to be formatted.
            decimals (int): the number of decimal places to be used.

        Returns:
            str: the formatted number.
        """
        return f"{round(number, decimals):.{decimals}f}"


class PeriodicInfoUpdate(PeriodicBehaviour):  # type: ignore
    def __init__(self, period: float, start_at: datetime | None = None):
        super().__init__(period, start_at)
        self.last_info = ""
        self.agent: SimpleAgent

    async def run(self) -> None:
        new_info = self.agent.get_info_message().body
        if self.last_info != new_info:
            self.last_info = new_info
            await self.agent.send_update("info")
