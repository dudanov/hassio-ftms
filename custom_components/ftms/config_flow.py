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
                            "options": list(cli.available_properties),
                            "multiple": True,
                            "translation_key": "sensors",
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

    _ble_info: BluetoothServiceInfoBleak | None
    _discovered_devices: dict[str, BluetoothServiceInfoBleak]
    _ftms: FitnessMachine | None = None

    _connect_task: asyncio.Task | None = None
    _discovery_task: asyncio.Task | None = None
    _close_task: asyncio.Task | None = None

    _discovery_time: float
    _suggested_sensors: list[str]

    def __init__(self) -> None:
        """Initialize the config flow."""

        self._ble_info = None
        self._discovered_devices = {}

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the user step to pick discovered device."""

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            self._ble_info = self._discovered_devices[address]

            return await self.async_step_confirm()

        configured = self._async_current_ids()

        for dev in async_discovered_service_info(self.hass):
            if dev.address in configured:
                continue

            try:
                get_machine_type_from_service_data(dev.advertisement)
                self._discovered_devices[dev.address] = dev

            except NotFitnessMachineError:
                pass

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        available_devices = {
            address: human_readable_name(None, dev.name, address)
            for address, dev in self._discovered_devices.items()
        }

        data_schema = vol.Schema(
            {
                vol.Required(CONF_ADDRESS): vol.In(available_devices),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
        )

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
        if user_input is not None:
            self._discovery_time = 30 if user_input[CONF_DISCOVERY] == "auto" else 0
            return await self.async_step_ble_request()

        # here we know device
        assert (info := self._ble_info)

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
        """BLE connection step."""

        if self._ftms is None:
            assert (info := self._ble_info)
            self._ftms = get_client(info.device, info.advertisement)

        uncompleted_task: asyncio.Task[None] | None = None

        if not uncompleted_task:
            if not self._connect_task:
                self._connect_task = self.hass.async_create_task(self._ftms.connect())

            if not self._connect_task.done():
                uncompleted_task, action = self._connect_task, "connecting"

        if not uncompleted_task:
            if self._discovery_time:
                if not self._discovery_task:
                    coro = asyncio.sleep(self._discovery_time)
                    self._discovery_task = self.hass.async_create_task(coro)

                if not self._discovery_task.done():
                    uncompleted_task, action = self._discovery_task, "discovering"

        if not uncompleted_task:
            if not self._close_task:
                self._close_task = self.hass.async_create_task(self._ftms.disconnect())

            if not self._close_task.done():
                uncompleted_task, action = self._close_task, "closing"

        if uncompleted_task:
            return self.async_show_progress(
                step_id="ble_request",
                progress_action=action,
                progress_task=uncompleted_task,
            )

        self._suggested_sensors = list(
            self._ftms.live_properties
            if self._discovery_task
            else self._ftms.supported_properties
        )

        _LOGGER.debug(f"Device Information: {self._ftms.device_info}")
        _LOGGER.debug(f"Machine type: {self._ftms.machine_type!r}")
        _LOGGER.debug(f"Available sensors: {self._ftms.available_properties}")
        _LOGGER.debug(f"Supported settings: {self._ftms.supported_settings}")
        _LOGGER.debug(f"Suggested sensors: {self._suggested_sensors}")

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
                            "options": list(self._ftms.available_properties),
                            "multiple": True,
                            "translation_key": "sensors",
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
