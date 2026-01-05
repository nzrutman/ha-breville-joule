"""Data models for the Breville Joule integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:
    from .coordinator import BrevilleJouleDataUpdateCoordinator


type BrevilleJouleConfigEntry = ConfigEntry[BrevilleJouleDataUpdateCoordinator]


@dataclass
class BrevilleJouleData:
    """Data from Breville Joule device."""

    current_temperature: float | None = None
    target_temperature: float | None = None
    start_time: str | None = None
    end_time: str | None = None
    is_active: bool = False
    serial_number: str | None = None


@dataclass
class BrevilleAppliance:
    """Breville appliance information."""

    serial_number: str
    model: str
    name: str | None = None
