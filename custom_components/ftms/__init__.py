"""The FTMS integration."""

import logging

import pyftms
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth.match import BluetoothCallbackMatcher
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_MAC,
    CONF_SENSORS,
    EVENT_HOMEASSISTANT_STOP,
    Platform,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .connect import ftms_connect
from .const import DOMAIN
from .coordinator import DataCoordinator
from .models import FtmsData

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SWITCH,
]

_LOGGER = logging.getLogger(__name__)

type FtmsConfigEntry = ConfigEntry[FtmsData]


async def async_unload_entry(hass: HomeAssistant, entry: FtmsConfigEntry) -> bool:
    """Unload a config entry."""

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.ftms.disconnect()

    return unload_ok


async def async_setup_entry(hass: HomeAssistant, entry: FtmsConfigEntry) -> bool:
    """Set up device from a config entry."""

    mac: str = entry.data[CONF_MAC]

    if not (srv_info := bluetooth.async_last_service_info(hass, mac)):
        raise ConfigEntryNotReady(
            translation_key="device_not_found",
            translation_placeholders={CONF_MAC: mac},
        )

    def _on_disconnect(ftms_: pyftms.FitnessMachine) -> None:
        """Disconnect handler. Reload entry on disconnect."""

        if ftms_.need_connect:
            raise ConfigEntryNotReady(
                translation_key="device_disconnected",
                translation_placeholders={CONF_MAC: mac},
            )

    ftms = pyftms.get_client(
        srv_info.device,
        srv_info.advertisement,
        on_disconnect=_on_disconnect,
    )

    coordinator = DataCoordinator(hass, ftms)

    await ftms_connect(ftms)

    assert ftms.machine_type.name

    unique_id = "".join(
        x.lower() for x in ftms.device_info.get("serial_number", mac) if x.isalnum()
    )

    device_info = dr.DeviceInfo(
        connections={(dr.CONNECTION_BLUETOOTH, ftms.address)},
        identifiers={(DOMAIN, unique_id)},
        translation_key=ftms.machine_type.name.lower(),
        **ftms.device_info,
    )

    entry.runtime_data = FtmsData(
        unique_id=unique_id,
        device_info=device_info,
        ftms=ftms,
        coordinator=coordinator,
        sensors=entry.options[CONF_SENSORS],
    )

    @callback
    def _async_on_ble_event(
        srv_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        """Update from a ble callback."""

        ftms.set_ble_device_and_advertisement_data(
            srv_info.device, srv_info.advertisement
        )

    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            _async_on_ble_event,
            BluetoothCallbackMatcher(address=mac),
            bluetooth.BluetoothScanningMode.ACTIVE,
        )
    )

    # Platforms initialization
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_entry_update_handler))

    async def _async_hass_stop_handler(event: Event) -> None:
        """Close the connection."""

        await ftms.disconnect()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_hass_stop_handler)
    )

    return True


async def _async_entry_update_handler(
    hass: HomeAssistant, entry: FtmsConfigEntry
) -> None:
    """Options update handler."""

    if entry.options[CONF_SENSORS] != entry.runtime_data.sensors:
        hass.config_entries.async_schedule_reload(entry.entry_id)
