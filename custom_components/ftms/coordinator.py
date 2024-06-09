"""Data coordinator for receiving FTMS events."""

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from pyftms import FitnessMachine, FtmsEvents

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class DataCoordinator(DataUpdateCoordinator[FtmsEvents]):
    """FTMS events coordinator."""

    def __init__(self, hass: HomeAssistant, ftms: FitnessMachine) -> None:
        """Initialize the coordinator."""

        def _on_ftms_event(data: FtmsEvents):
            self.async_set_updated_data(data)

        super().__init__(hass, _LOGGER, name=DOMAIN)

        ftms.set_callback(_on_ftms_event)
