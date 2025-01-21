from typing import Any

from src.agents.simple_agent import SimpleAgent


class BaseInteractionAgent(SimpleAgent):
    """
    Base class for every interaction agent that can exist in a network, added for future functionalities.
    """

    def __init__(
        self,
        *args: Any,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
