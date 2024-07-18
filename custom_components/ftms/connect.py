from bleak.exc import BleakError
from homeassistant.const import CONF_MAC
from homeassistant.exceptions import ConfigEntryNotReady
from pyftms import FitnessMachine


async def ftms_connect(ftms: FitnessMachine):
    try:
        await ftms.connect()
    except BleakError as exc:
        raise ConfigEntryNotReady(
            translation_key="connection_failed",
            translation_placeholders={CONF_MAC: ftms.address},
        ) from exc
