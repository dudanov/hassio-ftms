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


class _FakeInfo:
    def __init__(self, *, address=FTMS_ADDRESS, name="TRAINER"):
        self.address = address
        self.name = name
        self.advertisement = object()


class FtmsConfigFlowTests(unittest.TestCase):
    def tearDown(self):
        for name in [
            "custom_components.ftms.config_flow",
            "custom_components.ftms",
            "bluetooth_data_tools",
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

    def _load_module(self, *, discovered_infos, on_parse=None):
        package = types.ModuleType("custom_components.ftms")
        package.__path__ = [str(ROOT / "custom_components" / "ftms")]
        sys.modules["custom_components.ftms"] = package

        bluetooth_data_tools = types.ModuleType("bluetooth_data_tools")
        bluetooth_data_tools.human_readable_name = (
            lambda _a, name, address: name or address
        )
        sys.modules["bluetooth_data_tools"] = bluetooth_data_tools

        ha = types.ModuleType("homeassistant")
        ha_components = types.ModuleType("homeassistant.components")
        ha_bluetooth = types.ModuleType("homeassistant.components.bluetooth")
        ha_bluetooth.BluetoothServiceInfoBleak = object
        ha_bluetooth.async_discovered_service_info = lambda hass: discovered_infos
        ha_bluetooth.async_last_service_info = lambda hass, address: None
        sys.modules["homeassistant"] = ha
        sys.modules["homeassistant.components"] = ha_components
        sys.modules["homeassistant.components.bluetooth"] = ha_bluetooth

        class _FakeConfigFlow:
            def __init_subclass__(cls, **kwargs):
                super().__init_subclass__()

            def __init__(self):
                self.hass = object()

            def _async_current_ids(self):
                return set()

            def async_abort(self, *, reason):
                return {"type": "abort", "reason": reason}

            def async_show_form(self, **kwargs):
                return {"type": "form", **kwargs}

        ha_config_entries = types.ModuleType("homeassistant.config_entries")
        ha_config_entries.ConfigEntry = object
        ha_config_entries.ConfigFlow = _FakeConfigFlow
        ha_config_entries.ConfigFlowResult = dict
        ha_config_entries.OptionsFlow = object
        ha_config_entries.OptionsFlowWithConfigEntry = object
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

        def get_machine_type_from_service_data(advertisement):
            if on_parse is not None:
                on_parse()
            return object()

        pyftms.get_machine_type_from_service_data = get_machine_type_from_service_data
        sys.modules["pyftms"] = pyftms

        voluptuous = types.ModuleType("voluptuous")
        voluptuous.Schema = lambda value: value
        voluptuous.Required = lambda key: key
        voluptuous.In = lambda value: value
        sys.modules["voluptuous"] = voluptuous

        return importlib.import_module("custom_components.ftms.config_flow")

    def test_user_discovery_snapshots_candidates_before_parse(self):
        discovered_infos = {FTMS_ADDRESS: _FakeInfo()}

        def add_discovery():
            discovered_infos["00:00:5E:00:2E:44"] = _FakeInfo(
                address="00:00:5E:00:2E:44"
            )

        module = self._load_module(
            discovered_infos=discovered_infos.values(),
            on_parse=add_discovery,
        )
        flow = module.FTMSConfigFlow()

        result = asyncio.run(flow.async_step_user())

        self.assertEqual(result["type"], "form")
        self.assertEqual(flow._discovered_devices.keys(), {FTMS_ADDRESS})


if __name__ == "__main__":
    unittest.main()
