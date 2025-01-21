from datetime import datetime, timedelta, timezone, tzinfo
from typing import Any, Dict, Optional
from unittest.mock import patch

import pytest
from spade.behaviour import PeriodicBehaviour

from src.agents.common_behaviours.time_keeping_mixin import TimeKeepingMixin

TEST_DATETIME = datetime.fromtimestamp(0, tz=timezone.utc)
TEST_DATA: Dict[str, Any] = {
    "real_broadcast_time": {
        "value": "2005-01-01 12:34:56.360309",
    },
    "sim_broadcast_time": {
        "value": "2006-01-01 12:34:56.360309",
    },
    "rate": {"value": 2},
}


class FakeDateTime(datetime):
    def __new__(cls, *args: tuple[Any], **kwargs: dict[str, Any]) -> "FakeDateTime":
        return datetime.__new__(datetime, *args, **kwargs)  # type: ignore

    @classmethod
    def now(cls, tz: Optional[tzinfo] = None) -> Any:
        return TEST_DATETIME


class DummyBehavior(PeriodicBehaviour):  # type: ignore
    async def run(self) -> None:
        pass


def test_process_time_message() -> None:
    time_keeping_mixin = TimeKeepingMixin()
    time_keeping_mixin.process_time_message(TEST_DATA)

    assert time_keeping_mixin.real_broadcast_timestamp == datetime.fromisoformat(
        TEST_DATA["real_broadcast_time"]["value"]
    )
    assert time_keeping_mixin.sim_broadcast_timestamp == datetime.fromisoformat(
        TEST_DATA["sim_broadcast_time"]["value"]
    )
    assert time_keeping_mixin.rate == TEST_DATA["rate"]["value"]


def test_time_subscription() -> None:
    time_keeping_mixin = TimeKeepingMixin()
    sub_dict = time_keeping_mixin.time_subscription("test")

    assert sub_dict == {
        "time_agent@test": {"time": time_keeping_mixin.process_time_message}
    }


@patch("src.agents.common_behaviours.time_keeping_mixin.datetime", FakeDateTime)
def test_sim_timestamp() -> None:
    time_keeping_mixin = TimeKeepingMixin()

    sim_datetime = TEST_DATETIME - timedelta(seconds=30)

    time_keeping_mixin._real_broadcast_timestamp = sim_datetime
    time_keeping_mixin._sim_broadcast_timestamp = sim_datetime
    time_keeping_mixin._rate = 2.0

    expected_timetime = sim_datetime + timedelta(seconds=30) * time_keeping_mixin._rate

    assert time_keeping_mixin.sim_timestamp == expected_timetime


def test_rate_setter() -> None:
    time_keeping_mixin = TimeKeepingMixin()
    time_keeping_mixin._rate = 2.0
    time_keeping_mixin.behaviours.append(DummyBehavior(period=7))

    time_keeping_mixin.rate = 1.0

    for behavior in time_keeping_mixin.behaviours:
        if isinstance(behavior, PeriodicBehaviour):
            assert behavior.period.total_seconds() == 14.0


def test_to_datetime_no_parseable_datetime_or_string() -> None:
    time_keeping_mixin = TimeKeepingMixin()
    with pytest.raises(ValueError):
        time_keeping_mixin._to_datetime("Hello123")


def test_to_datetime_no_datetime_or_str() -> None:
    time_keeping_mixin = TimeKeepingMixin()
    with pytest.raises(TypeError):
        time_keeping_mixin._to_datetime(123)
