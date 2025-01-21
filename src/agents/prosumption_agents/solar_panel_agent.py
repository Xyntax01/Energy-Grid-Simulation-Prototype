from typing import Any, Dict, Optional

from aioxmpp import JID

from src.agents.common_behaviours.subscribeable_behaviour import SubscriptionBehaviour
from src.agents.common_behaviours.time_keeping_mixin import TimeKeepingMixin
from src.agents.prosumption_agents.base_prosumption_agent import BaseProsumptionAgent
from src.enums.component_types import ComponentType
from src.utils.logger import LoggerFactory
from src.utils.service_jids import get_weather_agent_jid


class SolarPanelAgent(TimeKeepingMixin, BaseProsumptionAgent):
    """
    Attributes:
        TEMPERATURE_COEFFICIENT (float): Temperature coefficient for efficiency calculation.
        NOMINAL_TEMPERATURE (int): Nominal temperature in Celsius.
        REFERENCE_IRRADIANCE (int): Standard test conditions irradiance in W/m².
        NOCT (int): Nominal Operating Cell Temperature.
    Methods:
        __init__(jid, max_power_usage_kw, factor, logger_factory, log_threshold, parent):
        setup():
            Configure the agent.
        calculate_cell_temperature(ambient_temp, solar_irradiance, wind_speed):
        calculate_efficiency(irradiance, temperature):
            Calculate the power adjustment of the solar panel based on irradiance and temperature.
        _process_weather_message(data):
        irradiance:
            Returns the sun irradiance.
        ambient_temperature:
            Returns the ambient temperature.
        ground_temperature:
            Returns the ground temperature.
        wind_speed_m_s:
            Returns the wind speed.
        cloud_coverage:
            Returns the cloud coverage.
        rain:
            Returns the rain.
        net_power_usage_kw:
            Returns the net power usage in kW.
        status:
    Note:
        This solar panel model is based on this source: https://eepower.com/technical-articles/how-is-solar-panel-efficiency-measured

    A power producing component based on photovoltaics with advanced performance modeling.
    """

    # Advanced panel characteristics
    TEMPERATURE_COEFFICIENT = -0.0036  # -0.36% per degree Celsius
    NOMINAL_TEMPERATURE = 25  # Nominal temperature in Celsius
    REFERENCE_IRRADIANCE = 1000  # W/m² standard test conditions
    NOCT = 45  # Nominal Operating Cell Temperature

    def __init__(
        self,
        jid: str,
        asset_type: str,
        max_power_usage_kw: Optional[float] = None,
        factor: Optional[float] = 1.0,
        logger_factory: Optional[LoggerFactory] = None,
        log_threshold: Optional[int] = None,
        parent: Optional[JID] = None,
    ):
        """
        Initialize the solar panel agent with weather subscription.

        Args:
            jid (str): Agent's Jabber ID
            max_power_usage_kw (float, optional): Maximum power usage
            logger_factory (LoggerFactory, optional): Logging configuration
            log_threshold (int, optional): Logging threshold
            parent (JID, optional): Parent agent
        """
        super().__init__(
            jid=jid,
            asset_type=asset_type,
            max_power_usage_kw=max_power_usage_kw,
            component_type=ComponentType.PRODUCER,
            logger_factory=logger_factory,
            log_threshold=log_threshold,
            parent=parent,
        )
        # Weather parameters
        self._irradiance = 0.0
        self._ambient_temperature = 0.0
        self._ground_temperature = 0.0
        self._wind_speed_m_s = 0.0
        self._cloud_coverage_okta = 0.0
        self._rain = 0.0

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

    def calculate_cell_temperature(
        self, ambient_temp: float, solar_irradiance: float, wind_speed: float
    ) -> float:
        """
        Calculate cell temperature with wind speed cooling effect using Sandia model.

        Args:
            ambient_temp (float): Ambient air temperature (°C)
            solar_irradiance (float): Solar irradiance (W/m²)
            wind_speed (float): Wind speed (m/s)

        Returns:
            float: Estimated cell temperature (°C)
        """
        # Sandia model parameters
        a = -3.47
        b = -0.0594
        deltaT = 3

        # Cell temperature calculation
        cell_temp = ambient_temp + (solar_irradiance / 1000) * (a + b * wind_speed) + deltaT

        return cell_temp

    def calculate_efficiency(self, irradiance: float, temperature: float) -> float:
        """
        Calculate the power_adjustment of the solar panel based on irradiance and temperature using Sandia model.

        Args:
            irradiance (float): Solar irradiance (W/m²)
            temperature (float): Ambient temperature (°C)

        Returns:
            float: power_adjustment of the solar panel
        """
        temperature_difference = temperature - self.NOMINAL_TEMPERATURE

        # Sandia model efficiency calculation
        efficiency = 1 - self.TEMPERATURE_COEFFICIENT * temperature_difference
        # Direct linear scaling of output with irradiance
        output_scaling = min(1.0, self._irradiance / self.REFERENCE_IRRADIANCE)

        # Performance calculation scaled by irradiance and efficiency
        power_adjustment = (
            self.max_power_usage_kw * output_scaling * max(0, efficiency) * self.factor
        )

        return power_adjustment

    def _process_weather_message(self, data: Dict[str, Any]) -> None:
        """
        Process incoming weather data and update internal state.

        Args:
            data (Dict[str, Any]): Weather data dictionary
        """
        self._irradiance = float(data["sun_irradiance"]["value"])
        self._ambient_temperature = float(data["ambient_temperature"]["value"])
        self._ground_temperature = float(data["ground_temperature"]["value"])
        self._wind_speed_m_s = float(data["wind_speed"]["value"])
        self._cloud_coverage_okta = float(data["cloud_coverage"]["value"])
        self._rain = float(data["rain"]["value"])

        self.send_power_update_to_parent()

    @property
    def irradiance(self) -> Optional[float]:
        """Returns the sun irradiance"""
        return self._irradiance

    @property
    def ambient_temperature(self) -> Optional[float]:
        """Returns the ambient temperature"""
        return self._ambient_temperature

    @property
    def ground_temperature(self) -> Optional[float]:
        """Returns the ground temperature"""
        return self._ground_temperature

    @property
    def wind_speed_m_s(self) -> Optional[float]:
        """Returns the wind speed"""
        return self._wind_speed_m_s

    @property
    def cloud_coverage(self) -> Optional[float]:
        """Returns the cloud coverage"""
        return self._cloud_coverage_okta

    @property
    def rain(self) -> Optional[float]:
        """Returns the rain"""
        return self._rain

    @property
    def net_power_usage_kw(self) -> float:
        power_adjustment = self.calculate_efficiency(
            self._irradiance, self._ambient_temperature
        )

        power_usage = -round(max(0, power_adjustment), 6)

        self.save_power_update(self.get_formatted_sim_timestamp(), power_usage)

        if power_usage > 0:
            self.print(f"Net power usage: {power_usage} kW")

        return power_usage

    @property
    def status(self) -> str:
        """
        Determine current operational status of solar panel.

        Returns:
            str: Current status ('off' or 'generating')
        """
        return "off" if self.net_power_usage_kw >= 0 else "generating"
