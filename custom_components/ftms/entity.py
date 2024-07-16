"""FTMS integration base entity."""

import logging

from homeassistant.core import callback
from homeassistant.helpers.entity import Entity, EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DataCoordinator, FtmsConfigEntry
from .models import FtmsData

_LOGGER = logging.getLogger(__name__)


class FtmsEntity(CoordinatorEntity[DataCoordinator], Entity):
    """Base Entity"""

    _attr_has_entity_name = True
    _attr_should_poll = False

    _data: FtmsData

    def __init__(
        self,
        entry: FtmsConfigEntry,
        description: EntityDescription,
    ) -> None:
        self.entity_description = description
        self._data = entry.runtime_data
        self._attr_unique_id = f"{self._data.unique_id}-{self.key}"
        self._attr_device_info = self._data.device_info
        self._attr_translation_key = self.key

        super().__init__(self._data.coordinator)

    @property
    def key(self) -> str:
        return self.entity_description.key

    @property
    def available(self) -> bool:
        return self.ftms.is_connected and super().available

    @property
    def ftms(self):
        return self._data.ftms

    @callback
    def _handle_coordinator_update(self) -> None:
        pass
