"""FTMS integration models."""

import dataclasses as dc

from homeassistant.helpers.device_registry import DeviceInfo
from pyftms import FitnessMachine

from .coordinator import DataCoordinator


@dc.dataclass(frozen=True, kw_only=True)
class FtmsData:
    """Data for the FTMS integration."""

    entry_id: str
    unique_id: str
    device_info: DeviceInfo
    ftms: FitnessMachine
    coordinator: DataCoordinator
    sensors: list[str]
