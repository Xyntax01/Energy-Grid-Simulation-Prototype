from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

from aioxmpp import JID

from src.agents.interaction_agents.base_interaction_agent import BaseInteractionAgent
from src.agents.interaction_agents.cpo_agent import CpoAgent
from src.agents.network_agent import NetworkAgent
from src.agents.prosumption_agents.base_prosumption_agent import BaseProsumptionAgent
from src.agents.prosumption_agents.charging_station_agent import ChargingStationAgent
from src.agents.prosumption_agents.solar_panel_agent import SolarPanelAgent
from src.agents.prosumption_agents.wind_turbine_agent import WindTurbineAgent
from src.agents.time_agent import TimeAgent
from src.agents.weather_agent import WeatherAgent
from src.utils.logger import LoggerFactory


class AgentFactory(ABC):
    """Abstract base class for creating Agent instances.

    Concrete factory classes must implement the following methods:

    * create_prosumption_base_agent()
    * create_interaction_agent()
    * create_network_agent()
    * create_time_agent()
    * create_weather_agent()
    """

    @staticmethod
    def _get_asset_dict() -> dict[str, type[BaseProsumptionAgent]]:
        """
        Get the prosumption_base_agent mapping dict with the string representations and which
        prosumption_base_agent class they map to.

        Returns:
            dict[str, type[BaseProsumptionAgent]]: mapping dict with the string
            representations and which asset class they map to.
        """
        return {
            "chargingstation": ChargingStationAgent,
            "solarpanel": SolarPanelAgent,
            "windturbine": WindTurbineAgent,
        }

    @staticmethod
    def _get_asset_class(
        asset_type: str,
    ) -> type[BaseProsumptionAgent]:
        """Get the prosumption_base_agent class for a given string representation.

        Args:
            asset_type (str): The string representation of the asset type.

        Raises:
            ValueError: Raised when an invalid type is given.

        Returns:
            type[BaseProsumptionAgent]: An asset class inheriting from BaseAsset.
        """
        try:
            return AgentFactory._get_asset_dict()[asset_type]
        except KeyError as err:
            raise ValueError(
                f"{asset_type} is not a valid asset_type and cannot be instantiated",
            ) from err

    @staticmethod
    @abstractmethod
    def create_asset(
        asset_type: str,
        jid: str,
        max_power_usage_kw: Optional[float] = None,
        logger_factory: Optional[LoggerFactory] = None,
        log_threshold: Optional[int] = None,
        parent: Optional[JID] = None,
        **kwargs: Any,
    ) -> BaseProsumptionAgent:
        """Create an instance of an prosumption_base_agent of the given type.

        Args:
            asset_type (str): the type of asset to produce
            jid (str): the jabber identifier of the asset agent
            max_power_usage_kw (float): the maximum power the asset can produce/consume/prosume
            logger_factory (Optional[LoggerFactory], optional): A factory to get a logger from. Defaults to None.
            log_threshold (Optional[int], optional): Level up until logs should be logged. Defaults to None.
            parent (Optional[JID], optional): The jabber id of the parent agent in the simulation. Defaults to None.
            kwargs: Remaining key word arguments
        Returns:
            BaseProsumptionAgent: An prosumption agent instance of the specified type.
        """
        asset_class = AgentFactory._get_asset_class(asset_type)

        return asset_class(
            jid=jid,
            asset_type=asset_type,
            max_power_usage_kw=max_power_usage_kw,
            parent=parent,
            logger_factory=logger_factory,
            log_threshold=log_threshold,
            **kwargs,
        )

    @staticmethod
    def _get_interaction_agent_dict() -> dict[str, type[BaseInteractionAgent]]:
        """
        Get the interaction_base_agent mapping dict with the string representations and which
        interaction_base_agent class they map to.

        Returns:
            dict[str, type[BaseInteractionAgent]]: mapping dict with the string
            representations and which asset class they map to.
        """
        return {
            "cpo": CpoAgent,
        }

    @staticmethod
    def _get_interaction_agent_class(
        interaction_agent_type: str,
    ) -> type[BaseInteractionAgent]:
        """Get the interaction_base_agent class for a given string representation.

        Args:
            interaction_agent_type (str): The string representation of the asset type.

        Raises:
            ValueError: Raised when an invalid type is given.

        Returns:
            type[BaseInteractionAgent]: An asset class inheriting from BaseAsset.
        """
        try:
            return AgentFactory._get_interaction_agent_dict()[interaction_agent_type]
        except KeyError as err:
            raise ValueError(
                f"{interaction_agent_type} is not a valid interaction_agent_type and cannot be instantiated",
            ) from err

    @staticmethod
    @abstractmethod
    def create_interaction_agent(
        interaction_agent_type: str,
        jid: str,
        password: str,
        logger_factory: Optional[LoggerFactory] = None,
        log_threshold: Optional[int] = None,
        **kwargs: Any,
    ) -> BaseInteractionAgent:
        """Create an instance of an base_interaction_agent of the given type.

        Args:
            interaction_agent_type (str): the type of asset to produce
            jid (str): the jabber identifier of the asset agent
            logger_factory (Optional[LoggerFactory], optional): A factory to get a logger from. Defaults to None.
            log_threshold (Optional[int], optional): Level up until logs should be logged. Defaults to None.
            parent (Optional[JID], optional): The jabber id of the parent agent in the simulation. Defaults to None.

        Returns:
            BaseInteractionAgent: An interaction agent instance of the specified type.
        """
        interaction_agent_class = AgentFactory._get_interaction_agent_class(
            interaction_agent_type
        )

        return interaction_agent_class(
            jid=jid,
            password=password,
            logger_factory=logger_factory,
            log_threshold=log_threshold,
        )

    @staticmethod
    @abstractmethod
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

    @staticmethod
    @abstractmethod
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

    @staticmethod
    @abstractmethod
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
