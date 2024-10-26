"""FTMS integration sensor platform."""

import logging

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.components.sensor.const import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfLength,
    UnitOfPower,
    UnitOfSpeed,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyftms import MovementDirection, TrainingStatusCode
from pyftms.client import const as c

from . import FtmsConfigEntry
from .const import TRAINING_STATUS
from .entity import FtmsEntity

_LOGGER = logging.getLogger(__name__)

_CADENCE_AVERAGE = SensorEntityDescription(
    key=c.CADENCE_AVERAGE,
    native_unit_of_measurement="rpm",
    state_class=SensorStateClass.MEASUREMENT,
)

_CADENCE_INSTANT = SensorEntityDescription(
    key=c.CADENCE_INSTANT,
    native_unit_of_measurement="rpm",
    state_class=SensorStateClass.MEASUREMENT,
)

_DISTANCE_TOTAL = SensorEntityDescription(
    key=c.DISTANCE_TOTAL,
    device_class=SensorDeviceClass.DISTANCE,
    native_unit_of_measurement=UnitOfLength.METERS,
    state_class=SensorStateClass.TOTAL,
)

_ELEVATION_GAIN_NEGATIVE = SensorEntityDescription(
    key=c.ELEVATION_GAIN_NEGATIVE,
    device_class=SensorDeviceClass.DISTANCE,
    native_unit_of_measurement=UnitOfLength.METERS,
    state_class=SensorStateClass.TOTAL,
)

_ELEVATION_GAIN_POSITIVE = SensorEntityDescription(
    key=c.ELEVATION_GAIN_POSITIVE,
    device_class=SensorDeviceClass.DISTANCE,
    native_unit_of_measurement=UnitOfLength.METERS,
    state_class=SensorStateClass.TOTAL,
)

_ENERGY_PER_HOUR = SensorEntityDescription(
    key=c.ENERGY_PER_HOUR,
    device_class=SensorDeviceClass.ENERGY,
    native_unit_of_measurement=UnitOfEnergy.KILO_CALORIE,
    state_class=SensorStateClass.MEASUREMENT,
)

_ENERGY_PER_MINUTE = SensorEntityDescription(
    key=c.ENERGY_PER_MINUTE,
    device_class=SensorDeviceClass.ENERGY,
    native_unit_of_measurement=UnitOfEnergy.KILO_CALORIE,
    state_class=SensorStateClass.MEASUREMENT,
)

_ENERGY_TOTAL = SensorEntityDescription(
    key=c.ENERGY_TOTAL,
    device_class=SensorDeviceClass.ENERGY,
    native_unit_of_measurement=UnitOfEnergy.KILO_CALORIE,
    state_class=SensorStateClass.TOTAL,
)

_FORCE_ON_BELT = SensorEntityDescription(
    key=c.FORCE_ON_BELT,
    native_unit_of_measurement="N",
    state_class=SensorStateClass.MEASUREMENT,
)

_HEART_RATE = SensorEntityDescription(
    key=c.HEART_RATE,
    native_unit_of_measurement="bpm",
    state_class=SensorStateClass.MEASUREMENT,
)

_INCLINATION = SensorEntityDescription(
    key=c.INCLINATION,
    native_unit_of_measurement="%",
    state_class=SensorStateClass.MEASUREMENT,
)

_METABOLIC_EQUIVALENT = SensorEntityDescription(
    key=c.METABOLIC_EQUIVALENT,
    native_unit_of_measurement="MET",
    state_class=SensorStateClass.MEASUREMENT,
)

_MOVEMENT_DIRECTION = SensorEntityDescription(
    key=c.MOVEMENT_DIRECTION,
    device_class=SensorDeviceClass.ENUM,
    options=[x.name.lower() for x in MovementDirection],
)

_PACE_AVERAGE = SensorEntityDescription(
    key=c.PACE_AVERAGE,
    device_class=SensorDeviceClass.DURATION,
    native_unit_of_measurement=UnitOfTime.MINUTES,
    state_class=SensorStateClass.MEASUREMENT,
)

_PACE_INSTANT = SensorEntityDescription(
    key=c.PACE_INSTANT,
    device_class=SensorDeviceClass.DURATION,
    native_unit_of_measurement=UnitOfTime.MINUTES,
    state_class=SensorStateClass.MEASUREMENT,
)

_POWER_AVERAGE = SensorEntityDescription(
    key=c.POWER_AVERAGE,
    device_class=SensorDeviceClass.POWER,
    native_unit_of_measurement=UnitOfPower.WATT,
    state_class=SensorStateClass.MEASUREMENT,
)

_POWER_INSTANT = SensorEntityDescription(
    key=c.POWER_INSTANT,
    device_class=SensorDeviceClass.POWER,
    native_unit_of_measurement=UnitOfPower.WATT,
    state_class=SensorStateClass.MEASUREMENT,
)

_POWER_OUTPUT = SensorEntityDescription(
    key=c.POWER_OUTPUT,
    device_class=SensorDeviceClass.POWER,
    native_unit_of_measurement=UnitOfPower.WATT,
    state_class=SensorStateClass.MEASUREMENT,
)

_RAMP_ANGLE = SensorEntityDescription(
    key=c.RAMP_ANGLE,
    native_unit_of_measurement="°",
    state_class=SensorStateClass.MEASUREMENT,
)

_RESISTANCE_LEVEL = SensorEntityDescription(
    key=c.RESISTANCE_LEVEL,
    state_class=SensorStateClass.MEASUREMENT,
)

_SPEED_AVERAGE = SensorEntityDescription(
    key=c.SPEED_AVERAGE,
    device_class=SensorDeviceClass.SPEED,
    native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
    state_class=SensorStateClass.MEASUREMENT,
)

_SPEED_INSTANT = SensorEntityDescription(
    key=c.SPEED_INSTANT,
    device_class=SensorDeviceClass.SPEED,
    native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
    state_class=SensorStateClass.MEASUREMENT,
)

_SPLIT_TIME_AVERAGE = SensorEntityDescription(
    key=c.SPLIT_TIME_AVERAGE,
    device_class=SensorDeviceClass.DURATION,
    native_unit_of_measurement=UnitOfTime.SECONDS,
    state_class=SensorStateClass.MEASUREMENT,
)

_SPLIT_TIME_INSTANT = SensorEntityDescription(
    key=c.SPLIT_TIME_INSTANT,
    device_class=SensorDeviceClass.DURATION,
    native_unit_of_measurement=UnitOfTime.SECONDS,
    state_class=SensorStateClass.MEASUREMENT,
)

_STEP_COUNT = SensorEntityDescription(
    key=c.STEP_COUNT,
    state_class=SensorStateClass.TOTAL,
)

_STEP_RATE_AVERAGE = SensorEntityDescription(
    key=c.STEP_RATE_AVERAGE,
    native_unit_of_measurement="min⁻¹",
    state_class=SensorStateClass.MEASUREMENT,
)

_STEP_RATE_INSTANT = SensorEntityDescription(
    key=c.STEP_RATE_INSTANT,
    native_unit_of_measurement="min⁻¹",
    state_class=SensorStateClass.MEASUREMENT,
)

_STRIDE_COUNT = SensorEntityDescription(
    key=c.STRIDE_COUNT,
    state_class=SensorStateClass.TOTAL,
)

_STROKE_COUNT = SensorEntityDescription(
    key=c.STROKE_COUNT,
    state_class=SensorStateClass.TOTAL,
)

_STROKE_RATE_AVERAGE = SensorEntityDescription(
    key=c.STROKE_RATE_AVERAGE,
    native_unit_of_measurement="min⁻¹",
    state_class=SensorStateClass.MEASUREMENT,
)

_STROKE_RATE_INSTANT = SensorEntityDescription(
    key=c.STROKE_RATE_INSTANT,
    native_unit_of_measurement="min⁻¹",
    state_class=SensorStateClass.MEASUREMENT,
)

_TIME_ELAPSED = SensorEntityDescription(
    key=c.TIME_ELAPSED,
    device_class=SensorDeviceClass.DURATION,
    native_unit_of_measurement=UnitOfTime.SECONDS,
    state_class=SensorStateClass.TOTAL,
)

_TIME_REMAINING = SensorEntityDescription(
    key=c.TIME_REMAINING,
    device_class=SensorDeviceClass.DURATION,
    native_unit_of_measurement=UnitOfTime.SECONDS,
    state_class=SensorStateClass.MEASUREMENT,
)

_TRAINING_STATUS = SensorEntityDescription(
    key=TRAINING_STATUS,
    device_class=SensorDeviceClass.ENUM,
    options=[x.name.lower() for x in TrainingStatusCode],
)

_ENTITIES = {
    c.CADENCE_AVERAGE: _CADENCE_AVERAGE,
    c.CADENCE_INSTANT: _CADENCE_INSTANT,
    c.DISTANCE_TOTAL: _DISTANCE_TOTAL,
    c.ELEVATION_GAIN_NEGATIVE: _ELEVATION_GAIN_NEGATIVE,
    c.ELEVATION_GAIN_POSITIVE: _ELEVATION_GAIN_POSITIVE,
    c.ENERGY_PER_HOUR: _ENERGY_PER_HOUR,
    c.ENERGY_PER_MINUTE: _ENERGY_PER_MINUTE,
    c.ENERGY_TOTAL: _ENERGY_TOTAL,
    c.FORCE_ON_BELT: _FORCE_ON_BELT,
    c.HEART_RATE: _HEART_RATE,
    c.INCLINATION: _INCLINATION,
    c.METABOLIC_EQUIVALENT: _METABOLIC_EQUIVALENT,
    c.MOVEMENT_DIRECTION: _MOVEMENT_DIRECTION,
    c.PACE_AVERAGE: _PACE_AVERAGE,
    c.PACE_INSTANT: _PACE_INSTANT,
    c.POWER_AVERAGE: _POWER_AVERAGE,
    c.POWER_INSTANT: _POWER_INSTANT,
    c.POWER_OUTPUT: _POWER_OUTPUT,
    c.RAMP_ANGLE: _RAMP_ANGLE,
    c.RESISTANCE_LEVEL: _RESISTANCE_LEVEL,
    c.SPEED_AVERAGE: _SPEED_AVERAGE,
    c.SPEED_INSTANT: _SPEED_INSTANT,
    c.SPLIT_TIME_AVERAGE: _SPLIT_TIME_AVERAGE,
    c.SPLIT_TIME_INSTANT: _SPLIT_TIME_INSTANT,
    c.STEP_COUNT: _STEP_COUNT,
    c.STEP_RATE_AVERAGE: _STEP_RATE_AVERAGE,
    c.STEP_RATE_INSTANT: _STEP_RATE_INSTANT,
    c.STRIDE_COUNT: _STRIDE_COUNT,
    c.STROKE_COUNT: _STROKE_COUNT,
    c.STROKE_RATE_AVERAGE: _STROKE_RATE_AVERAGE,
    c.STROKE_RATE_INSTANT: _STROKE_RATE_INSTANT,
    c.TIME_ELAPSED: _TIME_ELAPSED,
    c.TIME_REMAINING: _TIME_REMAINING,
}

_DEFAULT_VALUES = {
    c.MOVEMENT_DIRECTION: "forward",
    TRAINING_STATUS: "idle",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FtmsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a FTMS sensor entry."""

    data = entry.runtime_data

    entities = [
        FtmsSensorEntity(
            entry=entry,
            description=_ENTITIES[key],
        )
        for key in data.sensors
    ]

    entities.append(
        FtmsSensorEntity(
            entry=entry,
            description=_TRAINING_STATUS,
        )
    )

    async_add_entities(entities)


class FtmsSensorEntity(FtmsEntity, SensorEntity):
    """Representation of FTMS sensors."""

    def __init__(self, entry, description) -> None:
        self._attr_native_value = _DEFAULT_VALUES.get(description.key, 0)
        super().__init__(entry, description)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        e = self.coordinator.data

        if e.event_id == TRAINING_STATUS and self.key == TRAINING_STATUS:
            self._attr_native_value = e.event_data["code"].name.lower()
            self.async_write_ha_state()
            return

        if e.event_id == "update" and (value := e.event_data.get(self.key)) is not None:
            self._attr_native_value = value
            self.async_write_ha_state()
