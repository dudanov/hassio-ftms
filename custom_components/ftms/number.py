"""FTMS integration button platform."""

import logging
from typing import Any

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
)
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyftms.client import const as c

from . import FtmsConfigEntry
from .entity import FtmsEntity

_LOGGER = logging.getLogger(__name__)

_RESISTANCE_LEVEL: dict[str, Any] = {
    "key": c.TARGET_RESISTANCE,
    "icon": "mdi:chart-timeline-variant",
}

_POWER: dict[str, Any] = {
    "key": c.TARGET_POWER,
    "icon": "mdi:chart-timeline-variant",
    "device_class": NumberDeviceClass.POWER,
    "native_unit_of_measurement": UnitOfPower.WATT,
}


_ENTITIES = (
    _RESISTANCE_LEVEL,
    _POWER,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FtmsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a FTMS number entry."""

    entities, ranges_ = [], entry.runtime_data.ftms.supported_ranges

    for desc in _ENTITIES:
        if range_ := ranges_.get(desc["key"]):
            entities.append(
                FtmsNumberEntity(
                    entry=entry,
                    description=NumberEntityDescription(
                        native_min_value=range_.min_value,
                        native_max_value=range_.max_value,
                        native_step=range_.step,
                        **desc,
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

        e = self.coordinator.data

        if e.event_id == "setup":
            if (value := e.event_data.get(self.key)) is not None:
                self._attr_native_value = value
                self.async_write_ha_state()
