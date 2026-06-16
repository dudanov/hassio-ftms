import dataclasses
import importlib
import sys
import types
import unittest
from enum import Enum
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclasses.dataclass(frozen=True)
class _FakeSensorEntityDescription:
    key: str
    device_class: str | None = None
    native_unit_of_measurement: str | None = None
    state_class: str | None = None
    options: list[str] | None = None


class _FakeEnum(Enum):
    VALUE = 1


class _FakeFtmsEntity:
    pass


class _FakeSensorEntity:
    pass


def _install_fake_modules() -> None:
    package = types.ModuleType("custom_components.ftms")
    package.__path__ = [str(ROOT / "custom_components" / "ftms")]
    package.FtmsConfigEntry = object
    sys.modules["custom_components.ftms"] = package

    entity = types.ModuleType("custom_components.ftms.entity")
    entity.FtmsEntity = _FakeFtmsEntity
    sys.modules["custom_components.ftms.entity"] = entity

    ha_sensor = types.ModuleType("homeassistant.components.sensor")
    ha_sensor.SensorEntity = _FakeSensorEntity
    ha_sensor.SensorEntityDescription = _FakeSensorEntityDescription
    sys.modules["homeassistant.components.sensor"] = ha_sensor

    sensor_const = types.ModuleType("homeassistant.components.sensor.const")
    sensor_const.SensorDeviceClass = types.SimpleNamespace(
        DISTANCE="distance",
        DURATION="duration",
        ENERGY="energy",
        ENUM="enum",
        POWER="power",
        SPEED="speed",
    )
    sensor_const.SensorStateClass = types.SimpleNamespace(
        MEASUREMENT="measurement",
        TOTAL="total",
    )
    sys.modules["homeassistant.components.sensor.const"] = sensor_const

    ha_const = types.ModuleType("homeassistant.const")
    ha_const.UnitOfEnergy = types.SimpleNamespace(KILO_CALORIE="kcal")
    ha_const.UnitOfLength = types.SimpleNamespace(METERS="m")
    ha_const.UnitOfPower = types.SimpleNamespace(WATT="W")
    ha_const.UnitOfSpeed = types.SimpleNamespace(KILOMETERS_PER_HOUR="km/h")
    ha_const.UnitOfTime = types.SimpleNamespace(MINUTES="min", SECONDS="s")
    sys.modules["homeassistant.const"] = ha_const

    ha_core = types.ModuleType("homeassistant.core")
    ha_core.HomeAssistant = object
    ha_core.callback = lambda func: func
    sys.modules["homeassistant.core"] = ha_core

    entity_platform = types.ModuleType("homeassistant.helpers.entity_platform")
    entity_platform.AddEntitiesCallback = object
    sys.modules["homeassistant.helpers.entity_platform"] = entity_platform

    pyftms = types.ModuleType("pyftms")
    pyftms.MovementDirection = _FakeEnum
    pyftms.TrainingStatusCode = _FakeEnum
    sys.modules["pyftms"] = pyftms

    client = types.ModuleType("pyftms.client")
    sys.modules["pyftms.client"] = client

    const = types.ModuleType("pyftms.client.const")
    for name in [
        "CADENCE_AVERAGE",
        "CADENCE_INSTANT",
        "DISTANCE_TOTAL",
        "ELEVATION_GAIN_NEGATIVE",
        "ELEVATION_GAIN_POSITIVE",
        "ENERGY_PER_HOUR",
        "ENERGY_PER_MINUTE",
        "ENERGY_TOTAL",
        "FORCE_ON_BELT",
        "HEART_RATE",
        "INCLINATION",
        "METABOLIC_EQUIVALENT",
        "MOVEMENT_DIRECTION",
        "PACE_AVERAGE",
        "PACE_INSTANT",
        "POWER_AVERAGE",
        "POWER_INSTANT",
        "POWER_OUTPUT",
        "RAMP_ANGLE",
        "RESISTANCE_LEVEL",
        "SPEED_AVERAGE",
        "SPEED_INSTANT",
        "SPLIT_TIME_AVERAGE",
        "SPLIT_TIME_INSTANT",
        "STEP_COUNT",
        "STEP_RATE_AVERAGE",
        "STEP_RATE_INSTANT",
        "STRIDE_COUNT",
        "STROKE_COUNT",
        "STROKE_RATE_AVERAGE",
        "STROKE_RATE_INSTANT",
        "TIME_ELAPSED",
        "TIME_REMAINING",
        "TRAINING_STATUS",
    ]:
        setattr(const, name, name.lower())
    sys.modules["pyftms.client.const"] = const
    client.const = const


class FtmsSensorMetadataTests(unittest.TestCase):
    def tearDown(self):
        for name in list(sys.modules):
            if name.startswith(("custom_components.ftms", "homeassistant", "pyftms")):
                sys.modules.pop(name, None)

    def test_energy_rate_sensors_are_measurement_rates_not_energy_totals(self):
        _install_fake_modules()

        sensor = importlib.import_module("custom_components.ftms.sensor")

        energy_per_hour = sensor._ENTITIES["energy_per_hour"]
        energy_per_minute = sensor._ENTITIES["energy_per_minute"]
        self.assertIsNone(energy_per_hour.device_class)
        self.assertEqual(energy_per_hour.native_unit_of_measurement, "kcal/h")
        self.assertEqual(energy_per_hour.state_class, "measurement")
        self.assertIsNone(energy_per_minute.device_class)
        self.assertEqual(energy_per_minute.native_unit_of_measurement, "kcal/min")
        self.assertEqual(energy_per_minute.state_class, "measurement")


if __name__ == "__main__":
    unittest.main()
