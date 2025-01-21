import asyncio
import json
from copy import copy
from datetime import datetime
from typing import Any, Callable, Dict, Optional, TypedDict

from aioxmpp import JID
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from spade.template import Template


class MailingList(TypedDict):
    subscribers: list[JID]
    message_func: Callable[[Message], Message]


class PublishingAgentMixin(Agent):  # type: ignore
    """
    Agent add-on that allows other agents to subscribe to it and receive updates.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the agent.
        """
        super().__init__(*args, **kwargs)
        self.queues: Dict[str, MailingList] = {}

    async def setup(self) -> None:
        """
        Configure the agent behaviour
        """
        template = Template(metadata={"type": "subscribe"})
        self._subscription_receiver_behaviour = SubscriptionReceiverBehaviour()
        self.add_behaviour(self._subscription_receiver_behaviour, template=template)

    async def send_update(self, queue: str) -> None:
        """
        Send an update to all subscribers.
        """
        await self._subscription_receiver_behaviour.send_data(queue)


class SubscriptionReceiverBehaviour(CyclicBehaviour):  # type: ignore
    """
    Behaviour that receives subscription requests and sends data to subscribers.
    New subscribers get the last message once by default, in addition `send_data` can be called to send messages to specific or all subscribers.
    """

    def __init__(self) -> None:
        super().__init__()
        self.agent: PublishingAgentMixin

    async def run(self) -> None:
        """
        Handle incoming messages.
        """
        msg = await self.receive(timeout=1)

        if msg:
            if "queue" not in msg.metadata:
                self.agent.print(
                    "Received subscription request without queue from %s", msg.sender
                )
                return

            queue_name = msg.metadata["queue"]

            if queue_name not in self.agent.queues:
                self.agent.print(
                    "Received subscription request for missing queue %s from %s",
                    queue_name,
                    msg.sender,
                )
                return

            queue = self.agent.queues[queue_name]

            if msg.sender not in queue["subscribers"]:
                queue["subscribers"].append(msg.sender)
                await self.send_data(queue_name, msg.sender)

    def _get_recipients(self, queue: str, recipient: Optional[JID] = None) -> list[JID]:
        """
        Get a list of recipients for a message.

        Returns:
            list[JID]: the recipients of the message
        """
        if isinstance(recipient, JID):
            return [recipient]

        if queue not in self.agent.queues:
            raise ValueError(f"Agent does not have queue {queue}")

        if not recipient:
            return self.agent.queues[queue]["subscribers"]

        raise ValueError(
            f"Invalid recipient: should be JID or None, got {type(recipient)}"
        )

    async def send_data(self, queue: str, recipient: Optional[JID] = None) -> None:
        """
        Fetch the specified message from the agent class and send it to the subscriber(s).

        Args:
            receiver (Optional[JID]): the receiver of the message. If none is defined, all subscribers are addressed.
        """

        recipients = self._get_recipients(queue, recipient)
        msg = self.agent.queues[queue]["message_func"](Message())

        async def send_message(recipient: JID, msg: Message) -> None:
            msg_copy = copy(msg)
            msg_copy.to = str(recipient)
            await self.send(msg_copy)

        await asyncio.gather(
            *(send_message(recipient, msg) for recipient in recipients)
        )


class SubscriptionBehaviour(CyclicBehaviour):  # type:ignore
    """
    Behaviour that sends out subscription requests and receives the messages from subscriptions and
    lets agents process them by passing functions.
    """

    def __init__(
        self,
        subscriptions_dict: Dict[str, Dict[str, Callable[[Dict[str, Any]], None]]],
    ):
        """Initialize the behaviour.

        Args:
            subscriptions_dict (Dict[str, Callable[[Dict[str, Any]], None]]):
                a dictionary containing the queues of other agents that the agent
                wants to subscribe to and the functions used for processing the
                messages from the queues.
        """
        super().__init__()
        self.request_timeout_seconds = 30
        self.subscriptions_dict = subscriptions_dict
        self.request_dict = {
            (sub_jid, queue_name): datetime.now()
            for sub_jid, queues_dict in self.subscriptions_dict.items()
            for queue_name, _ in queues_dict.items()
        }

    async def run(self) -> None:
        """Tries to subscribe to the queue(s) of the specified agent(s), if there are subscriptions requests that are unfulfilled.
        Updates the agent's specified attributes based upon the received message"""
        if self.request_dict.keys():
            await self.send_subscription_request()

        await self.receive_subscription_message()

    async def send_subscription_request(self) -> None:
        """Sends a subscription request message to the agents and queues in the request dict.
        If the request process is taking longer than the set request timeout, the request will be removed from the request dict.
        """
        for (sub_jid, queue_name), init_time in list(self.request_dict.items()):
            if (
                datetime.now() - init_time
            ).total_seconds() > self.request_timeout_seconds:
                del self.request_dict[(sub_jid, queue_name)]
                continue

            message = Message()
            message.to = sub_jid
            message.body = ""
            message.set_metadata("type", "subscribe")
            message.set_metadata("queue", queue_name)

            await self.send(message)

    async def receive_subscription_message(self) -> None:
        """Receives the message from subscriptions and processes it using the corresponding function."""
        msg = await self.receive(timeout=1)

        if not msg:
            return

        queues_dict = self.subscriptions_dict.get(str(msg.sender))
        if queues_dict and (message_type_func := queues_dict.get(msg.metadata["type"])):
            data: Dict[str, Any] = json.loads(msg.body)
            message_type_func(data)

            if (
                sub_jid_and_queue := (str(msg.sender), msg.metadata["type"])
            ) in self.request_dict.keys():
                del self.request_dict[sub_jid_and_queue]
