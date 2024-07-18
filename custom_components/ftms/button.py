"""FTMS integration button platform."""

import logging
from typing import override

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyftms.client import const as c

from . import FtmsConfigEntry
from .entity import FtmsEntity

_LOGGER = logging.getLogger(__name__)

_ENTITIES = (
    c.RESET,
    c.STOP,
    c.START,
    c.PAUSE,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FtmsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a FTMS button entry."""

    entities = [
        FtmsButtonEntity(
            entry=entry,
            description=ButtonEntityDescription(key=description),
        )
        for description in _ENTITIES
    ]

    async_add_entities(entities)


class FtmsButtonEntity(FtmsEntity, ButtonEntity):
    """Representation of FTMS control buttons."""

    @override
    async def async_press(self) -> None:
        """Handle the button press."""
        if self.key == c.RESET:
            await self.ftms.reset()

        elif self.key == c.START:
            await self.ftms.start_resume()

        elif self.key == c.STOP:
            await self.ftms.stop()

        elif self.key == c.PAUSE:
            await self.ftms.pause()
