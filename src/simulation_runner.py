import asyncio
import os
import signal
from argparse import Namespace
from datetime import datetime
from typing import Any, Dict, Optional

import yaml
from aioxmpp import JID
from spade.agent import Agent

from src.agents.network_agent import NetworkAgent
from src.agents.prosumption_agents.base_prosumption_agent import BaseProsumptionAgent
from src.agents.time_agent import TimeAgent
from src.agents.weather_agent import WeatherAgent
from src.factories.agent_factory import AgentFactory
from src.utils.logger import LoggerFactory, valid_log_threshold

MAX_POWER_LABEL = "max_power_kw"
FACTOR = "factor"


# pylint: disable=too-many-instance-attributes
class SimulationRunner:
    """Runner class that sets up and starts the simulation based on the configuration file."""

    _weather_agent: WeatherAgent
    _time_agent: TimeAgent
    _main_network_agent: NetworkAgent

    def __init__(self, args: Namespace, agent_factory: AgentFactory) -> None:
        self.name = "Simulation Runner"
        self.networks: list[Agent] = []
        self.assets: list[Agent] = []
        self.prosumption_agents: list[BaseProsumptionAgent] = []
        self._simulation_rate: float
        self._start_sim_timestamp: datetime

        self.domain: str = args.domain
        self.configuration_file: str = args.configuration_file
        self.password: str = args.password
        self.logger_factory = LoggerFactory(
            logfile=args.logfile, default_log_threshold=args.log_threshold
        )
        self._agent_factory = agent_factory
        self.kill_now = False
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, *_: Any) -> None:
        self.kill_now = True

    async def run(self) -> None:
        await self._load_config()

        self._main_network_agent = next(
            (network for network in self.networks if network.name == "main_network"),
            None,
        )
        if not self._main_network_agent:
            raise IndexError(
                "No network agent named 'main_network' available in the simulation"
            )

        async with self._main_network_agent.client.connected():
            await self._time_agent.resume_simulation()
            while not self.kill_now:
                if self._time_agent.end_simulation():
                    self.exit_gracefully()
                await asyncio.sleep(1)

            for asset in self.assets:
                await asset.stop()

            for prosumption_agent in self.prosumption_agents:
                prosumption_agent.on_unavailable_handler()
                await prosumption_agent.stop()

            for network in self.networks:
                # Make sure we don't stop main_network before we are done
                if network.name != "main_network":
                    await network.stop()

            await self._weather_agent.stop()
            await self._time_agent.stop()

            # Stop main_network as last so we retain connectivity with xmpp server
            self._main_network_agent.show_end_result()
            await self._main_network_agent.stop()

    async def _load_config(self) -> None:
        config: Optional[Dict[str, Any]]
        if self.configuration_file is None or not os.path.exists(
            self.configuration_file
        ):
            raise FileNotFoundError(
                f"Could not open config at path {self.configuration_file}"
            )

        with open(
            self.configuration_file, "r", encoding="utf-8"
        ) as stream:  # unspecified-encoding: ignore
            config = yaml.safe_load(stream)
        await self._unpack_dict(config, self.domain, self.password)

    async def _unpack_dict(
        self,
        config: Any,
        domain: str,
        password: str,
        parent: Optional[JID] = None,
    ) -> None:
        """Unpack a config dictionary and create network and asset agents recursively.

        Args:
            config: the configuration to be unpacked
            domain: The domain name for messaging
            password: the password for messaging
            parent: the JID of the parent if it exists"""
        for key, value in config.items():
            log_threshold = None
            if "log_threshold" in value:
                log_threshold = valid_log_threshold(value["log_threshold"])

            if key == "network":
                await self._unpack_network(
                    value=value,
                    domain=domain,
                    password=password,
                    parent=parent,
                    log_threshold=log_threshold,
                )

            if key == "electric_vehicles":
                await self._unpack_list(
                    value=value,
                    domain=domain,
                    password=password,
                )

            if key == "asset":
                await self._unpack_asset(
                    value=value, domain=domain, password=password, parent=parent
                )
            elif key == "simulation_time":
                await self._unpack_simulation_time(value=value)
                self._weather_agent = await self._init_weather_agent()
            elif key == "interaction_asset":
                await self._unpack_interaction_agent(
                    value=value,
                    domain=domain,
                    password=password,
                )

    async def _unpack_simulation_time(self, value: dict[str, Any]) -> None:
        """Unpack the section `simulation_time` from the configuration file. handles the `rate` and `simulation_start_date` variables, which should be a float and an iso8601 format datetime.

        Args:
            value: A dictionary with string keys and the aforementioned variables.
        """
        # set the rate
        if "rate" in value:
            try:
                self._simulation_rate = float(value["rate"])
            except ValueError as exc:
                raise ValueError(
                    "Could not parse section simulation_time: rate could not be parsed"
                ) from exc
        else:
            raise ValueError(
                "Could not parse section simulation_time: rate was missing."
            )

        # set the start simulation date
        if "simulation_start_date" in value:
            try:
                self._start_sim_timestamp = datetime.fromisoformat(
                    value["simulation_start_date"]
                )
            except ValueError as exc:
                raise ValueError(
                    "Could not parse section simulation_time: simulation_start_date could not be parsed as an iso8601 format."
                ) from exc
        else:
            raise ValueError(
                "Could not parse section simulation_time: simulation_start_date was missing"
            )

        # set the end simulation date
        if "simulation_end_date" in value:
            try:
                self._end_sim_timestamp = datetime.fromisoformat(
                    value["simulation_end_date"]
                )
            except ValueError as exc:
                raise ValueError(
                    "Could not parse section simulation_time: simulation_start_date could not be parsed as an iso8601 format."
                ) from exc
        else:
            raise ValueError(
                "Could not parse section simulation_time: simulation_start_date was missing"
            )
        # initialize the time agent
        self._time_agent = await self._init_time_agent(
            rate=self._simulation_rate,
            start_sim_timestamp=self._start_sim_timestamp,
            _end_sim_timestamp=self._end_sim_timestamp,
        )

    async def _unpack_network(
        self,
        value: Dict[str, Any],
        domain: str,
        password: str,
        log_threshold: Optional[int] = None,
        parent: Optional[JID] = None,
    ) -> None:
        """Unpack the dict, create a network and start it."""
        jid = self._unpack_jid(value, domain)

        network = self._agent_factory.create_network_agent(
            jid=jid,
            parent=parent,
            logger_factory=self.logger_factory,
            log_threshold=log_threshold,
        )
        await network.start()
        self.networks.append(network)

        if "children" in list(value.keys()):
            for child in value["children"]:
                if isinstance(child, dict):
                    await self._unpack_dict(
                        child, domain, password=password, parent=network.jid
                    )

    async def _unpack_list(
        self,
        value: Dict[str, Any],
        domain: str,
        password: str,
    ) -> None:
        for child in value:
            if isinstance(child, dict):
                await self._unpack_dict(child, domain=domain, password=password)

    async def _unpack_asset(
        self,
        value: dict[str, Any],
        domain: str,
        password: str,
        parent: Optional[JID] = None,
    ) -> None:
        """Unpack the dict, create an asset of the given type and start it."""
        asset_type = str(value["type"])
        log_threshold: int = self.logger_factory.default_log_threshold
        if "log_threshold" in value:
            value_threshold = valid_log_threshold(value["log_threshold"])
            if value_threshold:
                log_threshold = value_threshold

        max_power_usage_kw = (
            float(value[MAX_POWER_LABEL]) if MAX_POWER_LABEL in value else None
        )

        factor = float(value[FACTOR]) if FACTOR in value else 1

        jid = self._unpack_jid(value, domain)
        args = dict(value["args"]) if "args" in value else dict([])
        try:
            asset = self._agent_factory.create_asset(
                asset_type=asset_type,
                jid=jid,
                max_power_usage_kw=max_power_usage_kw,
                factor=factor,
                logger_factory=self.logger_factory,
                log_threshold=log_threshold,
                parent=parent,
                **args,
            )
            await asset.start()
            self.prosumption_agents.append(asset)

            if "children" in list(value.keys()):
                child = value["children"]
                if isinstance(child, dict):
                    await self._unpack_dict(child, domain, password)

        except (ValueError, TypeError) as err:
            logger = self.logger_factory.get_logger(
                self.name, log_threshold=log_threshold
            )
            logger.warning(err)

    async def _init_weather_agent(self) -> WeatherAgent:
        """Initialize the weather agent."""
        weather_agent = self._agent_factory.create_weather_agent(
            domain=self.domain,
            logger_factory=self.logger_factory,
        )
        await weather_agent.start()
        return weather_agent

    async def _unpack_interaction_agent(
        self,
        value: dict[str, Any],
        domain: str,
        password: str,
    ) -> None:
        """Unpack the dict, create an interaction_agent of the given type and start it."""
        interaction_agent_type = str(value["type"])
        log_threshold: int = self.logger_factory.default_log_threshold
        if "log_threshold" in value:
            value_threshold = valid_log_threshold(value["log_threshold"])
            if value_threshold:
                log_threshold = value_threshold

        jid = self._unpack_jid(value, domain)
        args = dict(value["args"]) if "args" in value else dict([])
        try:
            interaction_agent = self._agent_factory.create_interaction_agent(
                interaction_agent_type=interaction_agent_type,
                jid=jid,
                password=password,
                logger_factory=self.logger_factory,
                log_threshold=log_threshold,
                **args,
            )
            await interaction_agent.start()
            self.assets.append(interaction_agent)
        except ValueError as err:
            logger = self.logger_factory.get_logger(
                self.name, log_threshold=log_threshold
            )
            logger.warning(err)

    async def _init_time_agent(
        self,
        start_sim_timestamp: Optional[datetime] = None,
        _end_sim_timestamp: Optional[datetime] = None,
        rate: Optional[float] = None,
    ) -> TimeAgent:
        """Initialize the time agent."""
        time_agent = self._agent_factory.create_time_agent(
            domain=self.domain,
            logger_factory=self.logger_factory,
            rate=rate if rate else self._simulation_rate,
            start_sim_timestamp=start_sim_timestamp
            if start_sim_timestamp
            else self._start_sim_timestamp,
            end_sim_timestamp=_end_sim_timestamp
            if _end_sim_timestamp
            else self._end_sim_timestamp,
        )
        await time_agent.start()
        return time_agent

    def _unpack_jid(self, value: dict[str, Any], domain: str) -> str:
        if "jid" in list(value.keys()):
            return str(value["jid"])
        return f"{value['name']}@{domain}"

    def are_all_agents_running(self) -> bool:
        """Check if all agents are running."""
        for agent in self.networks + self.assets:
            if not agent.is_alive():
                return False
        return True
