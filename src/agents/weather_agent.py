import asyncio
import json
import os
from datetime import datetime
from typing import Optional

import pandas as pd
from spade.behaviour import PeriodicBehaviour
from spade.message import Message

from src.agents.common_behaviours.subscribeable_behaviour import (
    MailingList,
    SubscriptionBehaviour,
)
from src.agents.common_behaviours.time_keeping_mixin import TimeKeepingMixin
from src.agents.simple_agent import SimpleAgent
from src.utils.logger import LoggerFactory
from src.utils.service_jids import get_weather_agent_jid


class WeatherAgent(
    TimeKeepingMixin, SimpleAgent
):  # pylint: disable=too-many-instance-attributes
    """
    Generate and distribute weather data.
    """

    DEFAULT_PERIOD: int = 10

    def __init__(
        self,
        domain: str,
        password: str = "password",
        logger_factory: Optional[LoggerFactory] = None,
        log_threshold: Optional[int] = None,
        period: Optional[int] = None,
    ) -> None:
        """
        Initialize the agent.

        Args:
            domain (str): the domain to use for message passing
            period (int, optional): the regeneration period of the behaviour in seconds.
        """
        jid = get_weather_agent_jid(domain)
        super().__init__(
            jid=jid,
            password=password,
            logger_factory=logger_factory,
            log_threshold=log_threshold,
        )
        if not period:
            period = self.DEFAULT_PERIOD

        self.next_datetime: Optional[datetime] = None
        self._irradiance: Optional[float] = None
        self._ambient_temperature: Optional[float] = None
        self._ground_temperature: Optional[float] = None
        self._sun_intensity: Optional[float] = None
        self._wind_speed_m_s: Optional[float] = None
        self._air_pressure: Optional[float] = None
        self._cloud_coverage: Optional[float] = None
        self._rain: Optional[float] = None
        self.weather_behaviour = WeatherBehaviour(period=period)
        self.queues["weather"] = MailingList(
            subscribers=[], message_func=self.get_weather_message
        )
        self.time_subscription_behaviour = SubscriptionBehaviour(
            {
                **self.time_subscription(self.jid.domain),
            }
        )

    async def setup(self) -> None:
        """
        Configure the agent.
        """
        await super().setup()
        self.add_behaviour(self.weather_behaviour)
        self.add_behaviour(self.time_subscription_behaviour)

    @property
    def irradience(self) -> Optional[float]:
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
    def sun_intensity(self) -> Optional[float]:
        """Returns the sun intensity"""
        return self._sun_intensity

    @property
    def wind_speed_m_s(self) -> Optional[float]:
        """Returns the wind speed"""
        return self._wind_speed_m_s

    @property
    def air_pressure(self) -> Optional[float]:
        """Returns the air pressure"""
        return self._air_pressure

    @property
    def cloud_coverage(self) -> Optional[float]:
        """Returns the cloud coverage"""
        return self._cloud_coverage

    @property
    def rain(self) -> Optional[float]:
        """Returns the rain"""
        return self._rain

    def get_weather_message(self, message: Message = Message()) -> Message:
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
        message.body = str(
            json.dumps(
                {
                    "sun_irradiance": {"unit": "W/m^2", "value": self._irradiance},
                    "ambient_temperature": {
                        "unit": "°C",
                        "value": self.ambient_temperature,
                    },
                    "ground_temperature": {
                        "unit": "°C",
                        "value": self.ground_temperature,
                    },
                    "sun_intensity": {
                        "unit": "factor (no unit)",
                        "value": self.sun_intensity,
                    },
                    "wind_speed": {
                        "unit": "m/s",
                        "value": self.wind_speed_m_s,
                    },
                    "air_pressure": {
                        "unit": "Pa",
                        "value": self.air_pressure,
                    },
                    "cloud_coverage": {
                        "unit": "okta",
                        "value": self.cloud_coverage,
                    },
                    "rain": {
                        "unit": "mm/hr",
                        "value": self.rain,
                    },
                }
            )
        )
        message.set_metadata("type", "weather")
        return message


class WeatherBehaviour(PeriodicBehaviour):  # type: ignore
    """
    Behaviour that generates weather parameters and triggers a broadcast.
    """

    def __init__(self, period: int) -> None:
        """
        Initialize the behaviour.

        Args:
            period (int): the regeneration period of the behaviour in seconds.
        """
        super().__init__(period=period)
        self.agent: WeatherAgent
        self.weather_data = self._read_weather_data()

    async def run(self) -> None:
        """
        Gets weather parameters.
        """
        await asyncio.sleep(0.5)
        self._generate_weather_data()
        self._print_current_values()
        await self.agent.send_update("weather")

    def _generate_weather_data(self) -> None:
        """
        Gets weather data from the dataset and update agent's attributes.
        """
        if self._should_update_weather_data():
            weather_data = self._fetch_weather_data()
            self._update_agent_weather_data(weather_data)

    def _should_update_weather_data(self) -> bool:
        """
        Determine if weather data should be updated based on the current time.
        """
        self.agent.print(
            f"Current time: {self.agent.sim_timestamp} | Next time: {self.agent.next_datetime}"
        )
        return self.agent.next_datetime is None or datetime.strptime(
            self.agent.sim_timestamp.strftime("%H:30:00"), "%H:%M:%S"
        ) >= datetime.strptime(
            self.agent.next_datetime.strftime("%H:%M:%S"), "%H:%M:%S"
        )

    def _read_weather_data(self) -> pd.DataFrame:
        """
        Read the weather data from the dataset.
        """
        data_path = os.path.join(
            os.path.dirname(__file__), "../data/ClimateNoordBrabant.csv"
        )
        return pd.read_csv(data_path)

    def _fetch_weather_data(self) -> pd.Series:
        """
        Fetch weather data from the dataset for the current simulation timestamp.
        """
        self.agent.print(f"Fetching weather data for {self.agent.sim_timestamp}")
        current_datetime = self.agent.sim_timestamp.strftime("0000-%m-%d %H:30:00")
        self.agent.next_datetime = self.agent.sim_timestamp + pd.Timedelta(hours=1)
        current_data = self.weather_data.loc[
            self.weather_data["Local []"] == current_datetime
        ]
        return current_data.iloc[0] if not current_data.empty else pd.Series()

    def _update_agent_weather_data(self, weather_data: pd.Series) -> None:
        """
        Update the agent's weather attributes with the fetched data.
        """
        if not weather_data.empty:
            self.agent._irradiance = weather_data["Irradiance [W/m^2]"]
            self.agent._ambient_temperature = weather_data[
                "T_ambient [Degrees Celsius]"
            ]
            self.agent._ground_temperature = weather_data["T_ground [Degrees Celsius]"]
            self.agent._sun_intensity = weather_data["Rain [mm/hr]"]  # temporary
            self.agent._wind_speed_m_s = weather_data["Wind [m/s]"]
            self.agent._cloud_coverage = weather_data["Cloud [okta]"]
            self.agent._air_pressure = weather_data["Pressure [Pa]"]
            self.agent._rain = weather_data["Rain [mm/hr]"]

    def _print_current_values(self) -> None:
        """
        Print the current values of the weather parameters to the terminal.
        """

        values = {
            "Sun irradiance": self.agent.irradience,
            "Ambient temperature": self.agent.ambient_temperature,
            "Ground temperature": self.agent.ground_temperature,
            "Sun intensity": self.agent.sun_intensity,
            "Wind speed": self.agent.wind_speed_m_s,
            "Cloud coverage": self.agent.cloud_coverage,
            "Air pressure": self.agent.air_pressure,
            "Rain": self.agent.rain,
        }

        for key, value in values.items():
            self.agent.print(f"{key} is now {value}")
