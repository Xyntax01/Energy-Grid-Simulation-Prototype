from typing import Any, Dict, Optional

from aioxmpp import JID
from spade.behaviour import CyclicBehaviour

from src.agents.common_behaviours.subscribeable_behaviour import SubscriptionBehaviour
from src.agents.common_behaviours.time_keeping_mixin import TimeKeepingMixin
from src.agents.prosumption_agents.base_prosumption_agent import BaseProsumptionAgent
from src.enums.component_types import ComponentType
from src.utils.logger import LoggerFactory
from src.utils.service_jids import get_weather_agent_jid


class WindTurbineAgent(TimeKeepingMixin, BaseProsumptionAgent):
    """
    Attributes:
        MIN_WIND_SPEED_M_S (float): Minimum wind speed in m/s for power generation.
        MAX_WIND_SPEED_M_S (float): Maximum wind speed in m/s for power generation.
    Methods:
        __init__(jid, max_power_usage_kw, factor, logger_factory, log_threshold, parent):
        setup():
            Configure the agent.
        net_power_usage_kw:
            Returns the net power usage in kW.
        wind_speed_m_s:
            Returns the wind speed.
        _process_weather_message(data):
        status:
            Returns the current status of the wind turbine.
        _is_wind_too_strong():
            Checks if the wind speed is too strong for operation.
        _is_wind_too_weak():
            Checks if the wind speed is too weak for operation.

        Note:
            A power producing component based on wind energy. This model is based on the source: https://ocw-preview.odl.mit.edu/courses/22-081j-introduction-to-sustainable-energy-fall-2010/1b8f7cf6954227383a323ce08ffe6ae6_MIT22_081JF10_lec05b.pdf
    """

    MIN_WIND_SPEED_M_S = 3.0
    MAX_WIND_SPEED_M_S = 25.0

    def __init__(
        self,
        jid: str,
        asset_type: str,
        max_power_usage_kw: float = 2000,
        factor: Optional[float] = 1.0,
        logger_factory: Optional[LoggerFactory] = None,
        log_threshold: Optional[int] = None,
        parent: Optional[JID] = None,
    ):
        """Initialize the component."""
        super().__init__(
            jid=jid,
            asset_type=asset_type,
            max_power_usage_kw=max_power_usage_kw,
            component_type=ComponentType.PRODUCER,
            logger_factory=logger_factory,
            log_threshold=log_threshold,
            parent=parent,
        )
        self._wind_speed_m_s = 1.0
        self.air_pressure = 1.225
        self.ambient_temperature = 21.0
        self.factor = factor
        self.subscription_behaviour = SubscriptionBehaviour(
            {
                get_weather_agent_jid(self.jid.domain): {
                    "weather": self._process_weather_message,
                },
            }
        )
        self.time_subscription_behaviour = SubscriptionBehaviour(
            {
                **self.time_subscription(self.jid.domain),
            }
        )

    async def setup(self) -> None:
        """Configure the agent"""
        await super().setup()
        self.add_behaviour(self.subscription_behaviour)
        self.add_behaviour(self.time_subscription_behaviour)

    def calculate_power_usage(self) -> float:
        """
        Calculate the power usage based on the wind speed, air pressure, and other factors.
        The formula used is P = 0.5 * (air_pressure / (R * T)) * A * V^3 * factor
        where:
        - P is the power (in Watts)
        - A is the swept area of the turbine blades (assumed to be 1 for simplicity)
        - V is the wind speed in m/s
        - Cp is the power coefficient (typically between 0.35 to 0.45, limited by Betz's Law to 0.593)
        """
        if self._is_wind_too_weak() or self._is_wind_too_strong():
            return 0.0

        # Constants
        # air_density = self.air_pressure / (287.05 * (self.ambient_temperature + 273.15))
        swept_area = 1.0  # Assumed to be 1 m² for simplicity
        air_density = 288.15
        power = 0.5 * air_density * swept_area * (self._wind_speed_m_s**3)

        return power * self.factor / 1000  # Return in kW

    @property
    def net_power_usage_kw(self) -> float:
        """Return the current net power usage of the component. A negative value means that this component is producing power."""
        power_usage = -self.calculate_power_usage()
        self.save_power_update(self.get_formatted_sim_timestamp(), power_usage)
        return power_usage

    @property
    def wind_speed_m_s(self) -> float:
        """Return the current wind speed."""
        return self._wind_speed_m_s

    @wind_speed_m_s.setter
    def wind_speed_m_s(self, value: float) -> None:
        """Set the current wind speed."""
        self._wind_speed_m_s = value
        self.send_power_update_to_parent()

    def _process_weather_message(self, data: Dict[str, Any]) -> None:
        self.wind_speed_m_s = float(data["wind_speed"]["value"])
        self.air_pressure = float(data["air_pressure"]["value"])
        self.ambient_temperature = float(data["ambient_temperature"]["value"])
        # self.print(f"Received wind_speed: {self.wind_speed_m_s} m/s")

    @property
    def status(self) -> str:
        if self._is_wind_too_strong():
            return "handbrake"

        if self._is_wind_too_weak():
            return "idle"

        return "generating"

    def _is_wind_too_strong(self) -> bool:
        return self.wind_speed_m_s > self.MAX_WIND_SPEED_M_S

    def _is_wind_too_weak(self) -> bool:
        return self.wind_speed_m_s < self.MIN_WIND_SPEED_M_S
