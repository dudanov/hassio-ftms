import asyncio
import importlib
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


FTMS_ADDRESS = "00:00:5E:00:2E:43"


class _FakeAbortFlow(Exception):
    pass


class _FakeBleakError(Exception):
    pass


class _FakeCharacteristic:
    def __init__(self, properties):
        self.properties = properties


class _FakeService:
    def __init__(self, characteristics):
        self._characteristics = characteristics

    def get_characteristic(self, uuid):
        return self._characteristics.get(uuid)


class _FakeServices:
    def __init__(self, services):
        self._services = services

    def get_service(self, uuid):
        return self._services.get(uuid)


class _FakeClient:
    def __init__(self, services):
        self.services = _FakeServices(services)
        self.is_connected = True
        self.disconnect_calls = 0

    async def disconnect(self):
        self.disconnect_calls += 1
        self.is_connected = False


class _FakeHass:
    def __init__(self, *, ble_device=None):
        self.ble_device = ble_device


class _FakeInfo:
    def __init__(self, *, name="TRAINER", advertisement=None, device=None):
        self.address = FTMS_ADDRESS
        self.name = name
        self.advertisement = advertisement or types.SimpleNamespace(ftms=True)
        self.device = device or object()


class FtmsConfigFlowTests(unittest.TestCase):
    def tearDown(self):
        for name in [
            "custom_components.ftms.config_flow",
            "custom_components.ftms",
            "bluetooth_data_tools",
            "bleak",
            "bleak.exc",
            "bleak_retry_connector",
            "homeassistant",
            "homeassistant.components",
            "homeassistant.components.bluetooth",
            "homeassistant.config_entries",
            "homeassistant.const",
            "homeassistant.core",
            "homeassistant.helpers",
            "homeassistant.helpers.selector",
            "pyftms",
            "voluptuous",
        ]:
            sys.modules.pop(name, None)

    def _load_module(self, *, client=None, connection_error=None, discovered_infos=None):
        calls = []

        package = types.ModuleType("custom_components.ftms")
        package.__path__ = [str(ROOT / "custom_components" / "ftms")]
        sys.modules["custom_components.ftms"] = package

        bluetooth_data_tools = types.ModuleType("bluetooth_data_tools")
        bluetooth_data_tools.human_readable_name = (
            lambda _a, name, address: name or address
        )
        sys.modules["bluetooth_data_tools"] = bluetooth_data_tools

        bleak = types.ModuleType("bleak")
        bleak.BleakClient = object
        bleak_exc = types.ModuleType("bleak.exc")
        bleak_exc.BleakError = _FakeBleakError
        sys.modules["bleak"] = bleak
        sys.modules["bleak.exc"] = bleak_exc

        async def establish_connection(**kwargs):
            calls.append(kwargs)
            if connection_error:
                raise connection_error
            return client

        bleak_retry_connector = types.ModuleType("bleak_retry_connector")
        bleak_retry_connector.establish_connection = establish_connection
        sys.modules["bleak_retry_connector"] = bleak_retry_connector

        ha = types.ModuleType("homeassistant")
        ha_components = types.ModuleType("homeassistant.components")
        ha_bluetooth = types.ModuleType("homeassistant.components.bluetooth")
        ha_bluetooth.BluetoothServiceInfoBleak = object
        ha_bluetooth.async_ble_device_from_address = (
            lambda hass, address: hass.ble_device
        )
        ha_bluetooth.async_discovered_service_info = (
            lambda hass: discovered_infos or []
        )
        ha_bluetooth.async_last_service_info = lambda hass, address: None
        sys.modules["homeassistant"] = ha
        sys.modules["homeassistant.components"] = ha_components
        sys.modules["homeassistant.components.bluetooth"] = ha_bluetooth

        class _FakeConfigFlow:
            def __init_subclass__(cls, **kwargs):
                super().__init_subclass__()

            def __init__(self):
                self.hass = None
                self.context = {}
                self._configured_ids = set()
                self._in_progress_ids = set()
                self._unique_id = None

            async def async_set_unique_id(
                self, unique_id, *, raise_on_progress=False
            ):
                if raise_on_progress and unique_id in self._in_progress_ids:
                    raise _FakeAbortFlow("already_in_progress")
                self._unique_id = unique_id

            def _abort_if_unique_id_configured(self):
                if self._unique_id in self._configured_ids:
                    raise _FakeAbortFlow("already_configured")

            def _async_current_ids(self):
                return self._configured_ids

            def async_abort(self, *, reason):
                return {"type": "abort", "reason": reason}

            def async_show_form(self, **kwargs):
                return {"type": "form", **kwargs}

            def add_suggested_values_to_schema(self, schema, values):
                return schema

        ha_config_entries = types.ModuleType("homeassistant.config_entries")
        ha_config_entries.ConfigEntry = object
        ha_config_entries.ConfigFlow = _FakeConfigFlow
        ha_config_entries.ConfigFlowResult = dict
        ha_config_entries.OptionsFlow = object

        class _FakeOptionsFlowWithConfigEntry:
            def __init__(self, config_entry):
                self.config_entry = config_entry

        ha_config_entries.OptionsFlowWithConfigEntry = _FakeOptionsFlowWithConfigEntry
        sys.modules["homeassistant.config_entries"] = ha_config_entries

        ha_const = types.ModuleType("homeassistant.const")
        ha_const.CONF_ADDRESS = "address"
        ha_const.CONF_DISCOVERY = "discovery"
        ha_const.CONF_SENSORS = "sensors"
        sys.modules["homeassistant.const"] = ha_const

        ha_core = types.ModuleType("homeassistant.core")
        ha_core.callback = lambda func: func
        sys.modules["homeassistant.core"] = ha_core

        ha_helpers = types.ModuleType("homeassistant.helpers")
        ha_selector = types.ModuleType("homeassistant.helpers.selector")
        ha_selector.selector = lambda value: value
        sys.modules["homeassistant.helpers"] = ha_helpers
        sys.modules["homeassistant.helpers.selector"] = ha_selector

        pyftms = types.ModuleType("pyftms")
        pyftms.FitnessMachine = object
        pyftms.NotFitnessMachineError = type("NotFitnessMachineError", (Exception,), {})
        pyftms.get_client = lambda *args, **kwargs: object()
        pyftms.get_machine_type_from_service_data = lambda advertisement: object()

        def get_machine_type_from_advertisement(advertisement):
            if getattr(advertisement, "ftms", False):
                return object()
            raise pyftms.NotFitnessMachineError

        pyftms.get_machine_type_from_advertisement = (
            get_machine_type_from_advertisement
        )
        sys.modules["pyftms"] = pyftms

        voluptuous = types.ModuleType("voluptuous")
        voluptuous.Schema = lambda value: value
        voluptuous.Required = lambda key: key
        voluptuous.In = lambda value: value
        sys.modules["voluptuous"] = voluptuous

        module = importlib.import_module("custom_components.ftms.config_flow")
        return module, calls

    def _flow(self, module, *, ble_device=None):
        flow = module.FTMSConfigFlow()
        flow.hass = _FakeHass(ble_device=ble_device)
        return flow

    def test_bluetooth_candidate_with_ftms_gatt_continues_to_confirm(self):
        client = _FakeClient(
            {
                "1826": _FakeService(
                    {"2ad2": _FakeCharacteristic(properties=["notify"])}
                )
            }
        )
        module, calls = self._load_module(client=client)
        flow = self._flow(module, ble_device=object())

        result = asyncio.run(flow.async_step_bluetooth(_FakeInfo()))

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "confirm")
        self.assertEqual(client.disconnect_calls, 1)
        self.assertEqual(calls[0]["services"], ["1826"])

    def test_bluetooth_candidate_without_ftms_gatt_service_aborts(self):
        client = _FakeClient({})
        module, _calls = self._load_module(client=client)
        flow = self._flow(module, ble_device=object())

        result = asyncio.run(flow.async_step_bluetooth(_FakeInfo()))

        self.assertEqual(result, {"type": "abort", "reason": "not_ftms_device"})
        self.assertEqual(client.disconnect_calls, 1)

    def test_polluted_advertisement_without_actual_ftms_aborts(self):
        client = _FakeClient({"180a": _FakeService({})})
        module, _calls = self._load_module(client=client)
        flow = self._flow(module, ble_device=object())

        result = asyncio.run(flow.async_step_bluetooth(_FakeInfo()))

        self.assertEqual(result, {"type": "abort", "reason": "not_ftms_device"})
        self.assertEqual(client.disconnect_calls, 1)

    def test_connection_failure_aborts_without_ignoring_device(self):
        module, calls = self._load_module(
            connection_error=_FakeBleakError("radio busy")
        )
        flow = self._flow(module, ble_device=object())

        result = asyncio.run(flow.async_step_bluetooth(_FakeInfo()))

        self.assertEqual(result, {"type": "abort", "reason": "cannot_verify_ftms"})
        self.assertEqual(len(calls), 1)
        self.assertFalse(hasattr(flow, "_ignored_addresses"))

    def test_user_discovery_filters_unverified_candidate_before_showing_form(self):
        client = _FakeClient({})
        info = _FakeInfo()
        module, calls = self._load_module(client=client, discovered_infos=[info])
        flow = self._flow(module, ble_device=object())

        result = asyncio.run(flow.async_step_user())

        self.assertEqual(result, {"type": "abort", "reason": "no_devices_found"})
        self.assertEqual(len(calls), 1)
        self.assertEqual(client.disconnect_calls, 1)

    def test_configured_device_suppresses_duplicate_before_verification(self):
        client = _FakeClient(
            {
                "1826": _FakeService(
                    {"2ad2": _FakeCharacteristic(properties=["notify"])}
                )
            }
        )
        module, calls = self._load_module(client=client)
        flow = self._flow(module, ble_device=object())
        flow._configured_ids.add(FTMS_ADDRESS)

        with self.assertRaises(_FakeAbortFlow):
            asyncio.run(flow.async_step_bluetooth(_FakeInfo()))

        self.assertEqual(calls, [])
        self.assertEqual(client.disconnect_calls, 0)

    def test_in_progress_device_suppresses_duplicate_before_verification(self):
        client = _FakeClient(
            {
                "1826": _FakeService(
                    {"2ad2": _FakeCharacteristic(properties=["notify"])}
                )
            }
        )
        module, calls = self._load_module(client=client)
        flow = self._flow(module, ble_device=object())
        flow._in_progress_ids.add(FTMS_ADDRESS)

        with self.assertRaises(_FakeAbortFlow):
            asyncio.run(flow.async_step_bluetooth(_FakeInfo()))

        self.assertEqual(calls, [])
        self.assertEqual(client.disconnect_calls, 0)


if __name__ == "__main__":
    unittest.main()
