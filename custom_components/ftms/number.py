"""FTMS integration button platform."""

import dataclasses as dc
import logging

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
)
from homeassistant.const import UnitOfPower, UnitOfSpeed
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyftms.client import const as c

from . import FtmsConfigEntry
from .entity import FtmsEntity

_LOGGER = logging.getLogger(__name__)

_NUMBERS_SENSORS_MAP = {
    c.TARGET_SPEED: c.SPEED_INSTANT,
    c.TARGET_INCLINATION: c.INCLINATION,
    c.TARGET_RESISTANCE: c.RESISTANCE_LEVEL,
    c.TARGET_POWER: c.POWER_INSTANT,
}

_SPEED = NumberEntityDescription(
    key=c.TARGET_SPEED,
    device_class=NumberDeviceClass.SPEED,
    native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
)

_INCLINATION = NumberEntityDescription(
    key=c.TARGET_INCLINATION,
    native_unit_of_measurement="%",
)

_RESISTANCE_LEVEL = NumberEntityDescription(
    key=c.TARGET_RESISTANCE,
)

_POWER = NumberEntityDescription(
    key=c.TARGET_POWER,
    device_class=NumberDeviceClass.POWER,
    native_unit_of_measurement=UnitOfPower.WATT,
)

_ENTITIES = (
    _RESISTANCE_LEVEL,
    _POWER,
    _SPEED,
    _INCLINATION,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FtmsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a FTMS number entry."""

    entities, ranges_ = [], entry.runtime_data.ftms.supported_ranges

    for desc in _ENTITIES:
        if range_ := ranges_.get(desc.key):
            entities.append(
                FtmsNumberEntity(
                    entry=entry,
                    description=dc.replace(
                        desc,
                        native_min_value=range_.min_value,
                        native_max_value=range_.max_value,
                        native_step=range_.step,
                    ),
                )
            )

    async_add_entities(entities)


class FtmsNumberEntity(FtmsEntity, NumberEntity):
    """Representation of FTMS numbers."""

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value from HA."""

        await self.ftms.set_setting(self.key, value)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        e, key = self.coordinator.data, self.key

        if e.event_id == "update":
            if (key := _NUMBERS_SENSORS_MAP.get(key)) is None:
                return

        elif e.event_id != "setup":
            return

        if (value := e.event_data.get(key)) is not None:
            self._attr_native_value = value
            self.async_write_ha_state()
