"""Config flow for Hoymiles S-Miles integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
import async_timeout
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    ENDPOINT_HEALTH,
)

_LOGGER = logging.getLogger(__name__)


async def validate_connection(
    hass: HomeAssistant, host: str, port: int, max_retries: int = 3
) -> dict[str, Any]:
    """Validate the connection to the Hoymiles S-Miles health API with retry logic."""
    url = f"http://{host}:{port}{ENDPOINT_HEALTH}"
    last_error = None
    
    for attempt in range(max_retries):
        try:
            async with async_timeout.timeout(10):
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            if attempt > 0:
                                _LOGGER.info(
                                    "Successfully connected to %s after %d attempts",
                                    url, attempt + 1
                                )
                            return {"title": f"Hoymiles S-Miles Bridge ({host})"}
                        elif response.status == 503:
                            # 503 is often transient - retry automatically
                            error_msg = (
                                f"Health endpoint returned 503 (attempt {attempt + 1}/{max_retries}). "
                                "Bridge may be busy with database operations."
                            )
                            _LOGGER.warning(error_msg)
                            last_error = ConnectionError(
                                "Health endpoint temporarily unavailable (503). "
                                "Bridge may be busy - automatic retry in progress."
                            )
                            
                            # Don't retry if this is the last attempt
                            if attempt < max_retries - 1:
                                _LOGGER.debug("Waiting 2 seconds before retry...")
                                await asyncio.sleep(2)
                                continue
                            else:
                                # All retries exhausted
                                raise last_error
                        else:
                            _LOGGER.error("Health endpoint returned HTTP %d", response.status)
                            raise ConnectionError(f"Health endpoint returned HTTP {response.status}")
        except aiohttp.ClientError as err:
            _LOGGER.error("Connection error to %s (attempt %d/%d): %s", url, attempt + 1, max_retries, err)
            last_error = ConnectionError("Cannot connect to Hoymiles S-Miles health API")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
                continue
            raise last_error from err
        except asyncio.TimeoutError as err:
            _LOGGER.error("Timeout connecting to %s (attempt %d/%d)", url, attempt + 1, max_retries)
            last_error = ConnectionError("Connection timeout - check host and port")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
                continue
            raise last_error from err
        except ConnectionError:
            # Re-raise ConnectionError as-is (no retry for explicit errors)
            raise
        except Exception as err:
            _LOGGER.error("Unexpected error connecting to %s: %s", url, err, exc_info=True)
            raise ConnectionError("Unexpected error occurred") from err
    
    # Should not reach here, but just in case
    if last_error:
        raise last_error
    raise ConnectionError("Failed to validate connection after retries")


class HoymilesSmilesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hoymiles S-Miles Bridge."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_connection(
                    self.hass,
                    user_input[CONF_HOST],
                    user_input[CONF_PORT],
                )
            except ConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Create unique ID based on host:port
                await self.async_set_unique_id(
                    f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
                )
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=info["title"],
                    data=user_input,
                )

        # Show form
        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default="192.168.1.31"): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.port,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> HoymilesSmilesOptionsFlow:
        """Get the options flow for this handler."""
        return HoymilesSmilesOptionsFlow(config_entry)


class HoymilesSmilesOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Hoymiles S-Miles Bridge."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=10, max=300)),
                }
            ),
        )

