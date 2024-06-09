"""FTMS integration sensor platform."""

import logging

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.components.sensor.const import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfLength, UnitOfPower, UnitOfSpeed, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyftms.client import const as c

from . import FtmsConfigEntry
from .entity import FtmsEntity

_LOGGER = logging.getLogger(__name__)

_CADENCE_INSTANT = SensorEntityDescription(
    key=c.CADENCE_INSTANT,
    native_unit_of_measurement="rpm",
    state_class=SensorStateClass.MEASUREMENT,
    icon="mdi:horizontal-rotate-counterclockwise",
)


_SPEED_INSTANT = SensorEntityDescription(
    key=c.SPEED_INSTANT,
    device_class=SensorDeviceClass.SPEED,
    native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
    state_class=SensorStateClass.MEASUREMENT,
)


_DISTANCE_TOTAL = SensorEntityDescription(
    key=c.DISTANCE_TOTAL,
    device_class=SensorDeviceClass.DISTANCE,
    native_unit_of_measurement=UnitOfLength.METERS,
    state_class=SensorStateClass.TOTAL,
    icon="mdi:map-marker-distance",
)

_RESISTANCE_LEVEL = SensorEntityDescription(
    key=c.RESISTANCE_LEVEL,
    icon="mdi:chart-timeline-variant",
)

_HEART_RATE = SensorEntityDescription(
    key=c.HEART_RATE,
    icon="mdi:heart-pulse",
    native_unit_of_measurement="bpm",
    state_class=SensorStateClass.MEASUREMENT,
)

_POWER_INSTANT = SensorEntityDescription(
    key=c.POWER_INSTANT,
    device_class=SensorDeviceClass.POWER,
    native_unit_of_measurement=UnitOfPower.WATT,
    state_class=SensorStateClass.MEASUREMENT,
)

_TIME_ELAPSED = SensorEntityDescription(
    key=c.TIME_ELAPSED,
    device_class=SensorDeviceClass.DURATION,
    native_unit_of_measurement=UnitOfTime.SECONDS,
    state_class=SensorStateClass.TOTAL,
    icon="mdi:timer-play",
)

_ENERGY_TOTAL = SensorEntityDescription(
    key=c.ENERGY_TOTAL,
    native_unit_of_measurement="kcal",
    state_class=SensorStateClass.TOTAL,
    icon="mdi:food",
)

_ENTITIES = {
    c.CADENCE_INSTANT: _CADENCE_INSTANT,
    c.SPEED_INSTANT: _SPEED_INSTANT,
    c.DISTANCE_TOTAL: _DISTANCE_TOTAL,
    c.RESISTANCE_LEVEL: _RESISTANCE_LEVEL,
    c.HEART_RATE: _HEART_RATE,
    c.POWER_INSTANT: _POWER_INSTANT,
    c.TIME_ELAPSED: _TIME_ELAPSED,
    c.ENERGY_TOTAL: _ENERGY_TOTAL,
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
        if key in _ENTITIES
    ]

    async_add_entities(entities)


class FtmsSensorEntity(FtmsEntity, SensorEntity):
    """Representation of FTMS sensors."""

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        e = self.coordinator.data

        if e.event_id == "update" and (value := e.event_data.get(self.key)) is not None:
            self._attr_native_value = value
            self.async_write_ha_state()
