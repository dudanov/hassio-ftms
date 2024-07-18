"""FTMS integration switch platform."""

import logging
from typing import Any, override

from bleak.exc import BleakError
from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.const import STATE_OFF, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import FtmsConfigEntry
from .entity import FtmsEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FtmsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a FTMS switch entry."""

    connection_switch = ConnectionSwitchEntity(
        entry=entry,
        description=SwitchEntityDescription(
            key="connection",
            device_class=SwitchDeviceClass.SWITCH,
            entity_category=EntityCategory.CONFIG,
        ),
    )

    async_add_entities([connection_switch])


class ConnectionSwitchEntity(FtmsEntity, SwitchEntity, RestoreEntity):
    """Representation of FTMS connection switch."""

    @override
    async def async_added_to_hass(self) -> None:
        """Call when the switch is added to hass."""
        state = await self.async_get_last_state()
        self._attr_is_on = True

        if state is not None and state.state == STATE_OFF:
            await self.ftms.disconnect()
            self._attr_is_on = False

        await super().async_added_to_hass()

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""

        try:
            await self.ftms.connect()

        except BleakError:
            self.hass.config_entries.async_schedule_reload(self._data.entry_id)

        finally:
            self._attr_is_on = True
            self.async_write_ha_state()

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""

        await self.ftms.disconnect()
        self._attr_is_on = False
        self.async_write_ha_state()

    @property
    @override
    def available(self) -> bool:
        return True
