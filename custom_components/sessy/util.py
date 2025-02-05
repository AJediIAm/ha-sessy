from __future__ import annotations
from datetime import datetime, timedelta
from enum import Enum
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.dispatcher import async_dispatcher_send

from sessypy.const import SessyApiCommand
from sessypy.devices import SessyDevice, SessyBattery, SessyP1Meter, SessyCTMeter

from .const import DOMAIN, SESSY_CACHE, SESSY_CACHE_TRACKERS, SESSY_CACHE_TRIGGERS, SESSY_DEVICE, UPDATE_TOPIC, DEFAULT_SCAN_INTERVAL

async def add_cache_command(hass: HomeAssistant, config_entry: ConfigEntry, command: SessyApiCommand, interval: timedelta = DEFAULT_SCAN_INTERVAL):
    if not command in hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE]:
        hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE][command] = dict()

    async def update(event_time_utc: datetime = None):
        device: SessyDevice = hass.data[DOMAIN][config_entry.entry_id][SESSY_DEVICE]
        cache: dict = hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE]

        try:
            result = await device.api.get(command)
            cache[command] = result
        except:
            result = None
            cache[command] = None

        async_dispatcher_send(hass, UPDATE_TOPIC.format(command))

    if command in hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE_TRACKERS]:
        # Remove running tracker to avoid duplicates
        hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE_TRACKERS][command]()

    hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE_TRACKERS][command] = async_track_time_interval(hass, update, interval)
    hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE_TRIGGERS][command] = update
    await update()

async def clear_cache_command(hass: HomeAssistant, config_entry: ConfigEntry, command: SessyApiCommand = None):
    trackers = hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE_TRACKERS]
    if command == None:

        for tracker_command in trackers:
            tracker = trackers[tracker_command]
            tracker()
    else:
        tracker = trackers[command]
        tracker()


async def trigger_cache_update(hass: HomeAssistant, config_entry: ConfigEntry, command: SessyApiCommand):
    update = hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE_TRIGGERS][command]
    await update()

def backend_status_string(status_string: str, prefix: str = "") -> str:
    return status_string.removeprefix(prefix).lower()

def status_string_p1(status_string: str) -> str:
    return backend_status_string(status_string, "P1_")

def status_string_system_state(status_string: str) -> str:
    return backend_status_string(status_string, "SYSTEM_STATE_")

def status_string_power_strategy(status_string: str) -> str:
    return backend_status_string(status_string, "POWER_STRATEGY_")

def divide_by_thousand(input: int) -> float:
    return input / 1000

def only_negative_as_positive(input: int) -> int:
    return min(input, 0) * -1

def only_positive(input: int) -> int:
    return max(input, 0)

def enum_to_options_list(options: Enum, transform_function: function = None) -> list[str]:
    output = list()
    for option in options:
        value = option.value
        if transform_function:
            output.append(transform_function(value))
        else:
            output.append(value)
    return output


def unit_interval_to_percentage(input: float) -> float:
    return round(input * 100,1)

async def generate_device_info(hass: HomeAssistant, config_entry: ConfigEntry, device: SessyDevice) -> DeviceInfo:
    
    model = "Sessy Device"
    if isinstance(device, SessyBattery):
        model = "Sessy Battery"
    elif isinstance(device, SessyP1Meter):
        model = "Sessy P1 Dongle"
    elif isinstance(device, SessyCTMeter):
        model = "Sessy CT Dongle"

    # Generate Device Info
    device_info = DeviceInfo(
        name=device.name,
        manufacturer="Charged B.V.",
        identifiers={(DOMAIN, device.serial_number)},
        configuration_url=f"http://{device.host}/",
        model=model
    )

    return device_info
