from datetime import datetime
from typing import Any, Optional

from aioxmpp import JID

from src.agents.interaction_agents.base_interaction_agent import BaseInteractionAgent
from src.agents.network_agent import NetworkAgent
from src.agents.prosumption_agents.base_prosumption_agent import BaseProsumptionAgent
from src.agents.time_agent import TimeAgent
from src.agents.weather_agent import WeatherAgent
from src.factories.agent_factory import AgentFactory
from src.utils.logger import LoggerFactory


class RealAgentFactory(AgentFactory):
    """Factory for creating Agent instances

    This is useful in production environments. Agents will be as they are
    without any mocks or patches.
    """

    @classmethod
    def create_asset(
        cls,
        asset_type: str,
        jid: str,
        max_power_usage_kw: Optional[float] = None,
        logger_factory: Optional[LoggerFactory] = None,
        log_threshold: Optional[int] = None,
        parent: Optional[JID] = None,
        **kwargs: Any,
    ) -> BaseProsumptionAgent:
        """create an instance of an prosumption agent of the given type.

        Args:
            asset_type (str): the type of asset to produce
            jid (str): the jabber identifier of the asset agent
            logger_factory (Optional[LoggerFactory], optional): A factory to get a logger from. Defaults to None.
            log_threshold (Optional[int], optional): Level up until logs should be logged. Defaults to None.
            parent (Optional[JID], optional): The jabber id of the parent agent in the simulation. Defaults to None.

        Returns:
            BaseProsumptionAgent: An asset agent instance of the specified type.
        """
        asset_class = cls._get_asset_class(asset_type)

        return asset_class(
            jid=jid,
            asset_type=asset_type,
            max_power_usage_kw=max_power_usage_kw,
            parent=parent,
            logger_factory=logger_factory,
            log_threshold=log_threshold,
            **kwargs,
        )

    @classmethod
    def create_interaction_agent(
        cls,
        interaction_agent_type: str,
        jid: str,
        password: str,
        logger_factory: Optional[LoggerFactory] = None,
        log_threshold: Optional[int] = None,
        **kwargs: Any,
    ) -> BaseInteractionAgent:
        """create an instance of an prosumption agent of the given type.

        Args:
            domain (str): The domainname of the xmpp server
            logger_factory (Optional[LoggerFactory], optional): A factory to get a logger from. Defaults to None.
            log_threshold (Optional[int], optional): Level up until logs should be logged. Defaults to None.
        Returns:
            BaseInteractionAgent: An asset agent instance of the specified type.
        """
        interaction_agent_class = cls._get_interaction_agent_class(
            interaction_agent_type
        )

        return interaction_agent_class(
            jid=jid,
            password=password,
            logger_factory=logger_factory,
            log_threshold=log_threshold,
            **kwargs,
        )

    @staticmethod
    def create_network_agent(
        jid: str,
        logger_factory: Optional[LoggerFactory] = None,
        log_threshold: Optional[int] = None,
        parent: Optional[JID] = None,
    ) -> NetworkAgent:
        """Create an instance of NetworkAgent

        Args:
            jid (str): the jabber identifier of the network agent
            logger_factory (Optional[LoggerFactory], optional): A factory to get a logger from. Defaults to None.
            log_threshold (Optional[int], optional): Level up until logs should be logged. Defaults to None.
            parent (Optional[JID], optional): The jabber id of the parent agent in the simulation. Defaults to None.

        Returns:
            NetworkAgent: A network agent instance
        """
        return NetworkAgent(
            jid,
            parent=parent,
            logger_factory=logger_factory,
            log_threshold=log_threshold,
        )

    @staticmethod
    def create_time_agent(
        domain: str,
        start_sim_timestamp: datetime,
        end_sim_timestamp: datetime,
        rate: float,
        logger_factory: Optional[LoggerFactory] = None,
        log_threshold: Optional[int] = None,
    ) -> TimeAgent:
        """Create an instance of TimeAgent

        Args:
            domain (str): The domainname of the xmpp server
            start_sim_timestamp (datetime): The initial simulation moment
            end_sim_timestamp (datetime): The final simulation moment
            rate (float): The speed factor to run the simulation at. 1 = realtime
            logger_factory (Optional[LoggerFactory], optional): A factory to get a logger from. Defaults to None.
            log_threshold (Optional[int], optional): Level up until logs should be logged. Defaults to None.

        Returns:
            TimeAgent: A time agent instance
        """
        return TimeAgent(
            domain=domain,
            rate=rate,
            start_sim_timestamp=start_sim_timestamp,
            end_sim_timestamp=end_sim_timestamp,
            logger_factory=logger_factory,
            log_threshold=log_threshold,
        )

    @staticmethod
    def create_weather_agent(
        domain: str,
        logger_factory: Optional[LoggerFactory] = None,
        log_threshold: Optional[int] = None,
        period: Optional[int] = None,
    ) -> WeatherAgent:
        """Create an instance of WeatherAgent

        Args:
            domain (str): The domainname of the xmpp server
            logger_factory (Optional[LoggerFactory], optional): A factory to get a logger from. Defaults to None.
            log_threshold (Optional[int], optional): Level up until logs should be logged. Defaults to None.
            period (Optional[int], optional): the regeneration period of weather in seconds. Defaults to None.

        Returns:
            WeatherAgent: A weather agent instance
        """
        return WeatherAgent(
            domain=domain,
            logger_factory=logger_factory,
            log_threshold=log_threshold,
            period=period,
        )
