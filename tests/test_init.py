import asyncio
import importlib
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class _FakeConfigEntryNotReady(Exception):
    def __init__(self, message: str = "", *, translation_key: str | None = None):
        super().__init__(message)
        self.translation_key = translation_key
        self.translation_placeholders = None


class _FakeBleakError(Exception):
    pass


_CONNECT_OK = object()
_CONNECT_HANG = object()
_CONNECT_CANCELLED = object()
FAKE_ADDRESS = "00:00:5E:00:53:01"
FAKE_NAME = "TRAINER BIKE 1234"
FAKE_MANUFACTURER = "Example Fitness"
FAKE_SERIAL = "123456789"


class _FakeConfigEntry:
    def __class_getitem__(cls, item):
        return cls


class _FakeDataCoordinator:
    def __init__(self, hass, ftms):
        self.hass = hass
        self.ftms = ftms


class _FakeFtmsData:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _FakeMachine:
    def __init__(self, result: Exception | object | None):
        self._result = result
        self.disconnect_calls = 0
        self.address = FAKE_ADDRESS
        self.name = FAKE_NAME
        self.device_info = {
            "manufacturer": FAKE_MANUFACTURER,
            "serial_number": FAKE_SERIAL,
        }
        self.machine_type = types.SimpleNamespace(name="INDOOR_BIKE")
        self.available_properties = ["power_instant"]
        self.supported_settings = []
        self.supported_ranges = {}
        self.is_connected = False

    async def connect(self):
        if self._result is _CONNECT_OK:
            self.is_connected = True
            return
        if self._result is _CONNECT_HANG:
            await asyncio.sleep(60)
        if self._result is _CONNECT_CANCELLED:
            raise asyncio.CancelledError()
        raise self._result

    async def disconnect(self):
        self.disconnect_calls += 1
        self.is_connected = False

    def set_ble_device_and_advertisement_data(self, device, advertisement):
        pass


class _FakeHass:
    def __init__(self, entry=None, *, is_stopping=False):
        self.is_stopping = is_stopping
        self.updated_entries = []
        self.forwarded_entries = []
        self.config_entries = types.SimpleNamespace(
            async_get_entry=lambda entry_id: entry,
            async_update_entry=self.async_update_entry,
            async_forward_entry_setups=self.async_forward_entry_setups,
        )
        self.bus = types.SimpleNamespace(async_listen_once=lambda event, listener: None)

    def async_update_entry(self, entry, **kwargs):
        self.updated_entries.append((entry, kwargs))
        if "title" in kwargs:
            entry.title = kwargs["title"]

    async def async_forward_entry_setups(self, entry, platforms):
        self.forwarded_entries.append((entry, platforms))


class _FakeEntry:
    def __init__(self, address: str):
        self.data = {"address": address}
        self.options = {"sensors": []}
        self.entry_id = "entry-1"
        self.title = f"FTMS GENERIC ({address})"
        self.unload_callbacks = []

    def async_on_unload(self, callback):
        self.unload_callbacks.append(callback)

    def add_update_listener(self, listener):
        return None


class FtmsInitTests(unittest.TestCase):
    def tearDown(self):
        for name in [
            "custom_components.ftms",
            "custom_components.ftms.coordinator",
            "custom_components.ftms.models",
            "pyftms",
            "bleak",
            "bleak.exc",
            "homeassistant",
            "homeassistant.components",
            "homeassistant.components.bluetooth",
            "homeassistant.components.bluetooth.match",
            "homeassistant.config_entries",
            "homeassistant.const",
            "homeassistant.core",
            "homeassistant.exceptions",
            "homeassistant.helpers",
            "homeassistant.helpers.device_registry",
        ]:
            sys.modules.pop(name, None)

    def _load_module(self, result: Exception | object | None):
        fake_machine = _FakeMachine(result)

        pyftms = types.ModuleType("pyftms")
        pyftms.get_client = lambda *args, **kwargs: fake_machine
        pyftms.NotFitnessMachineError = type("NotFitnessMachineError", (Exception,), {})
        pyftms.FitnessMachine = object
        sys.modules["pyftms"] = pyftms

        bleak = types.ModuleType("bleak")
        bleak_exc = types.ModuleType("bleak.exc")
        bleak_exc.BleakError = _FakeBleakError
        sys.modules["bleak"] = bleak
        sys.modules["bleak.exc"] = bleak_exc

        ha = types.ModuleType("homeassistant")
        ha_components = types.ModuleType("homeassistant.components")
        ha_bluetooth = types.ModuleType("homeassistant.components.bluetooth")
        ha_bluetooth.async_last_service_info = (
            lambda hass, address: types.SimpleNamespace(
                device=object(), advertisement=object()
            )
        )
        ha_bluetooth.async_register_callback = (
            lambda hass, callback, matcher, mode: None
        )
        ha_bluetooth.BluetoothChange = object
        ha_bluetooth.BluetoothScanningMode = types.SimpleNamespace(ACTIVE="active")
        ha_match = types.ModuleType("homeassistant.components.bluetooth.match")
        ha_match.BluetoothCallbackMatcher = lambda **kwargs: kwargs
        ha_config_entries = types.ModuleType("homeassistant.config_entries")
        ha_config_entries.ConfigEntry = _FakeConfigEntry
        ha_const = types.ModuleType("homeassistant.const")
        ha_const.CONF_ADDRESS = "address"
        ha_const.CONF_SENSORS = "sensors"
        ha_const.EVENT_HOMEASSISTANT_STOP = "stop"
        ha_const.Platform = types.SimpleNamespace(
            BUTTON="button",
            NUMBER="number",
            SENSOR="sensor",
            SWITCH="switch",
        )
        ha_core = types.ModuleType("homeassistant.core")
        ha_core.Event = object
        ha_core.HomeAssistant = object
        ha_core.callback = lambda func: func
        ha_exceptions = types.ModuleType("homeassistant.exceptions")
        ha_exceptions.ConfigEntryNotReady = _FakeConfigEntryNotReady
        ha_helpers = types.ModuleType("homeassistant.helpers")
        ha_device_registry = types.ModuleType("homeassistant.helpers.device_registry")
        ha_device_registry.CONNECTION_BLUETOOTH = "bluetooth"
        ha_device_registry.DeviceInfo = dict

        sys.modules["homeassistant"] = ha
        sys.modules["homeassistant.components"] = ha_components
        sys.modules["homeassistant.components.bluetooth"] = ha_bluetooth
        sys.modules["homeassistant.components.bluetooth.match"] = ha_match
        sys.modules["homeassistant.config_entries"] = ha_config_entries
        sys.modules["homeassistant.const"] = ha_const
        sys.modules["homeassistant.core"] = ha_core
        sys.modules["homeassistant.exceptions"] = ha_exceptions
        sys.modules["homeassistant.helpers"] = ha_helpers
        sys.modules["homeassistant.helpers.device_registry"] = ha_device_registry

        coordinator = types.ModuleType("custom_components.ftms.coordinator")
        coordinator.DataCoordinator = _FakeDataCoordinator
        models = types.ModuleType("custom_components.ftms.models")
        models.FtmsData = _FakeFtmsData
        sys.modules["custom_components.ftms.coordinator"] = coordinator
        sys.modules["custom_components.ftms.models"] = models

        module = importlib.import_module("custom_components.ftms")
        return module, fake_machine

    def test_async_setup_entry_is_idempotent_when_runtime_is_connected(self):
        module, _machine = self._load_module(RuntimeError("should not create client"))
        hass = _FakeHass()
        entry = _FakeEntry(FAKE_ADDRESS)
        entry.runtime_data = types.SimpleNamespace(
            ftms=types.SimpleNamespace(is_connected=True)
        )

        result = asyncio.run(module.async_setup_entry(hass, entry))

        self.assertTrue(result)

    def test_async_setup_entry_stops_if_entry_removed_after_connect(self):
        module, machine = self._load_module(_CONNECT_OK)
        hass = _FakeHass(entry=None)
        entry = _FakeEntry(FAKE_ADDRESS)

        result = asyncio.run(module.async_setup_entry(hass, entry))

        self.assertFalse(result)
        self.assertEqual(machine.disconnect_calls, 1)

    def test_async_setup_entry_updates_title_after_device_info_read(self):
        module, machine = self._load_module(_CONNECT_OK)
        entry = _FakeEntry(FAKE_ADDRESS)
        hass = _FakeHass(entry=entry)

        result = asyncio.run(module.async_setup_entry(hass, entry))

        self.assertTrue(result)
        self.assertEqual(machine.disconnect_calls, 0)
        self.assertEqual(
            hass.updated_entries,
            [
                (
                    entry,
                    {"title": "Example Fitness TRAINER BIKE 1234 (123456789)"},
                )
            ],
        )
        self.assertEqual(entry.title, "Example Fitness TRAINER BIKE 1234 (123456789)")

    def test_async_setup_entry_maps_timeout_to_startup_timeout(self):
        module, machine = self._load_module(TimeoutError("read timed out"))
        hass = _FakeHass()
        entry = _FakeEntry(FAKE_ADDRESS)

        with self.assertLogs("custom_components.ftms", level="WARNING") as logs:
            with self.assertRaises(_FakeConfigEntryNotReady) as ctx:
                asyncio.run(module.async_setup_entry(hass, entry))

        self.assertEqual(ctx.exception.translation_key, "startup_timeout")
        self.assertEqual(machine.disconnect_calls, 1)
        self.assertIn(FAKE_ADDRESS, "\n".join(logs.output))
        self.assertIn("retry setup automatically", "\n".join(logs.output))

    def test_async_setup_entry_times_out_hung_connect(self):
        module, machine = self._load_module(_CONNECT_HANG)
        module.STARTUP_TIMEOUT = 0.01
        hass = _FakeHass()
        entry = _FakeEntry(FAKE_ADDRESS)

        with self.assertLogs("custom_components.ftms", level="WARNING") as logs:
            with self.assertRaises(_FakeConfigEntryNotReady) as ctx:
                asyncio.run(module.async_setup_entry(hass, entry))

        self.assertEqual(ctx.exception.translation_key, "startup_timeout")
        self.assertEqual(machine.disconnect_calls, 1)
        self.assertIn(FAKE_ADDRESS, "\n".join(logs.output))

    def test_async_setup_entry_maps_cancelled_connect_to_connection_failed(self):
        module, machine = self._load_module(_CONNECT_CANCELLED)
        hass = _FakeHass()
        entry = _FakeEntry(FAKE_ADDRESS)

        with self.assertLogs("custom_components.ftms", level="WARNING") as logs:
            with self.assertRaises(_FakeConfigEntryNotReady) as ctx:
                asyncio.run(module.async_setup_entry(hass, entry))

        self.assertEqual(ctx.exception.translation_key, "connection_failed")
        self.assertEqual(machine.disconnect_calls, 1)
        self.assertIn(FAKE_ADDRESS, "\n".join(logs.output))
        self.assertIn("retry setup automatically", "\n".join(logs.output))

    def test_async_setup_entry_preserves_cancelled_connect_while_stopping(self):
        module, machine = self._load_module(_CONNECT_CANCELLED)
        hass = _FakeHass(is_stopping=True)
        entry = _FakeEntry(FAKE_ADDRESS)

        with self.assertRaises(asyncio.CancelledError):
            asyncio.run(module.async_setup_entry(hass, entry))

        self.assertEqual(machine.disconnect_calls, 0)

    def test_async_setup_entry_keeps_bleak_error_as_connection_failed(self):
        module, machine = self._load_module(_FakeBleakError("radio busy"))
        hass = _FakeHass()
        entry = _FakeEntry(FAKE_ADDRESS)

        with self.assertLogs("custom_components.ftms", level="WARNING") as logs:
            with self.assertRaises(_FakeConfigEntryNotReady) as ctx:
                asyncio.run(module.async_setup_entry(hass, entry))

        self.assertEqual(ctx.exception.translation_key, "connection_failed")
        self.assertEqual(machine.disconnect_calls, 1)
        self.assertIn(FAKE_ADDRESS, "\n".join(logs.output))
        self.assertIn("retry setup automatically", "\n".join(logs.output))


if __name__ == "__main__":
    unittest.main()
