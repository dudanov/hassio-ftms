"""Config flow for FTMS integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol
from bluetooth_data_tools import human_readable_name
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
    async_last_service_info,
)
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
    OptionsFlowWithConfigEntry,
)
from homeassistant.const import CONF_ADDRESS, CONF_DISCOVERY, CONF_SENSORS
from homeassistant.core import callback
from homeassistant.helpers.selector import selector
from pyftms import (
    FitnessMachine,
    NotFitnessMachineError,
    get_client,
    get_machine_type_from_service_data,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class OptionsFlowHandler(OptionsFlowWithConfigEntry):
    def __init__(self, config_entry: ConfigEntry) -> None:
        super().__init__(config_entry)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Options Handler."""

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        address = self.config_entry.data[CONF_ADDRESS]

        if not (srv_info := async_last_service_info(self.hass, address)):
            return self.async_abort(reason="no_devices_found")

        cli = get_client(srv_info.device, srv_info.advertisement)

        schema = vol.Schema(
            {
                vol.Required(CONF_SENSORS): selector(
                    {
                        "select": {
                            "multiple": True,
                            "options": list(cli.available_properties),
                            "translation_key": CONF_SENSORS,
                        }
                    }
                )
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(schema, self.options),
        )


class FTMSConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for FTMS."""

    VERSION = 1

    _ble_info: BluetoothServiceInfoBleak
    _discovered_devices: dict[str, BluetoothServiceInfoBleak]
    _discovery_time: float
    _suggested_sensors: list[str]

    _ftms: FitnessMachine | None = None
    _task1: asyncio.Task[None] | None = None
    _task2: asyncio.Task[None] | None = None
    _task3: asyncio.Task[None] | None = None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlow:
        """Create the options flow"""

        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the user step to pick discovered device."""

        if user_input is not None:
            addr = user_input[CONF_ADDRESS]

            self._ble_info = self._discovered_devices[addr]
            return await self.async_step_confirm()

        already_configured = self._async_current_ids()
        self._discovered_devices = {}

        for info in async_discovered_service_info(self.hass):
            if info.address in already_configured:
                continue

            try:
                get_machine_type_from_service_data(info.advertisement)

            except NotFitnessMachineError:
                continue

            self._discovered_devices[info.address] = info

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        devices = {
            addr: human_readable_name(None, dev.name, addr)
            for addr, dev in self._discovered_devices.items()
        }

        schema = vol.Schema({vol.Required(CONF_ADDRESS): vol.In(devices)})

        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_bluetooth(
        self,
        info: BluetoothServiceInfoBleak,
    ) -> ConfigFlowResult:
        """Handle the bluetooth discovery step."""

        try:
            get_machine_type_from_service_data(info.advertisement)

        except NotFitnessMachineError:
            return self.async_abort(reason="not_supported")

        await self.async_set_unique_id(info.address, raise_on_progress=True)
        self._abort_if_unique_id_configured()

        self._ble_info = info
        return await self.async_step_confirm()

    async def async_step_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Choosing properties discovering method"""

        if user_input is not None:
            self._discovery_time = 30 if user_input[CONF_DISCOVERY] == "auto" else 0
            return await self.async_step_ble_request()

        # here we know device
        info = self._ble_info
        placeholders = {"name": human_readable_name(None, info.name, info.address)}
        self.context["title_placeholders"] = placeholders

        schema = vol.Schema(
            {
                vol.Required(CONF_DISCOVERY): selector(
                    {
                        "select": {
                            "options": ["auto", "manual"],
                            "translation_key": CONF_DISCOVERY,
                        }
                    }
                ),
            }
        )

        return self.async_show_form(
            step_id="confirm",
            data_schema=self.add_suggested_values_to_schema(
                schema, {CONF_DISCOVERY: "auto"}
            ),
            description_placeholders=placeholders,
        )

    async def async_step_ble_request(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Connection and data collection step"""

        if self._ftms is None:
            info = self._ble_info
            self._ftms = get_client(info.device, info.advertisement)

        uncompleted_task: asyncio.Task[None] | None = None
        ftms = self._ftms

        if not uncompleted_task:
            if not self._task1:
                coro = ftms.connect()
                self._task1 = self.hass.async_create_task(coro)

            if not self._task1.done():
                uncompleted_task, action = self._task1, "connecting"

        if not uncompleted_task and self._discovery_time:
            if not self._task2:
                coro = asyncio.sleep(self._discovery_time)
                self._task2 = self.hass.async_create_task(coro)

            if not self._task2.done():
                uncompleted_task, action = self._task2, "discovering"

        if not uncompleted_task:
            if not self._task3:
                coro = ftms.disconnect()
                self._task3 = self.hass.async_create_task(coro)

            if not self._task3.done():
                uncompleted_task, action = self._task3, "closing"

        if uncompleted_task:
            return self.async_show_progress(
                step_id="ble_request",
                progress_action=action,
                progress_task=uncompleted_task,
            )

        self._suggested_sensors = list(
            ftms.live_properties if self._task2 else ftms.supported_properties
        )

        _LOGGER.debug("Device Information: %s", ftms.device_info)
        _LOGGER.debug("Machine type: %r", ftms.machine_type)
        _LOGGER.debug("Available sensors: %s", ftms.available_properties)
        _LOGGER.debug("Supported settings: %s", ftms.supported_settings)
        _LOGGER.debug("Supported ranges: %s", ftms.supported_ranges)
        _LOGGER.debug("Suggested sensors: %s", self._suggested_sensors)

        return self.async_show_progress_done(next_step_id="information")

    async def async_step_information(self, user_input=None):
        assert self._ftms

        if user_input is not None:
            unique_id = self._ftms.address
            await self.async_set_unique_id(unique_id, raise_on_progress=False)

            s1 = self._ftms.device_info.get("manufacturer", "FTMS")
            s2 = self._ftms.device_info.get("model", "GENERIC")
            s3 = f"({self._ftms.device_info.get("serial_number", unique_id)})"

            return self.async_create_entry(
                title=" ".join((s1, s2, s3)),
                data={CONF_ADDRESS: self._ftms.address},
                options={CONF_SENSORS: user_input[CONF_SENSORS]},
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_SENSORS): selector(
                    {
                        "select": {
                            "multiple": True,
                            "options": list(self._ftms.available_properties),
                            "translation_key": CONF_SENSORS,
                        }
                    }
                ),
            }
        )

        return self.async_show_form(
            step_id="information",
            data_schema=self.add_suggested_values_to_schema(
                schema, {CONF_SENSORS: self._suggested_sensors}
            ),
        )
