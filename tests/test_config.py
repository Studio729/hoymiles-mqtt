"""Tests for configuration module."""

import pytest
from pathlib import Path
from pydantic import ValidationError

from hoymiles_smiles.config import (
    AppConfig,
    DtuConfig,
    ModbusConfig,
    TimingConfig,
)


def test_dtu_config_valid():
    """Test valid DTU configuration."""
    config = DtuConfig(name="TestDTU", host="192.168.1.100", port=502, unit_id=1)
    assert config.name == "TestDTU"
    assert config.host == "192.168.1.100"
    assert config.port == 502
    assert config.unit_id == 1


def test_dtu_config_invalid_host():
    """Test DTU configuration with invalid host."""
    with pytest.raises(ValidationError):
        DtuConfig(name="TestDTU", host="", port=502)


def test_dtu_config_invalid_port():
    """Test DTU configuration with invalid port."""
    with pytest.raises(ValidationError):
        DtuConfig(name="TestDTU", host="192.168.1.100", port=0)
    
    with pytest.raises(ValidationError):
        DtuConfig(name="TestDTU", host="192.168.1.100", port=70000)


def test_modbus_config_valid():
    """Test valid Modbus configuration."""
    config = ModbusConfig(
        timeout=3,
        retries=3,
        reconnect_delay=1,
        reconnect_delay_max=300,
    )
    assert config.timeout == 3
    assert config.retries == 3
    assert config.reconnect_delay == 1
    assert config.reconnect_delay_max == 300


def test_modbus_config_invalid_delays():
    """Test Modbus configuration with invalid delay settings."""
    with pytest.raises(ValidationError):
        ModbusConfig(reconnect_delay=400, reconnect_delay_max=300)


def test_timing_config_valid():
    """Test valid timing configuration."""
    config = TimingConfig(
        query_period=60,
        expire_after=120,
        reset_hour=23,
        timezone="America/New_York",
    )
    assert config.query_period == 60
    assert config.expire_after == 120
    assert config.reset_hour == 23
    assert config.timezone == "America/New_York"


def test_timing_config_invalid_expire_after():
    """Test timing configuration with invalid expire_after."""
    with pytest.raises(ValidationError):
        TimingConfig(query_period=60, expire_after=30)


def test_app_config_single_dtu():
    """Test app configuration with single DTU."""
    config = AppConfig(
        dtu_host="192.168.1.100",
    )
    
    dtu_configs = config.get_dtu_configs()
    assert len(dtu_configs) == 1
    assert dtu_configs[0].host == "192.168.1.100"


def test_app_config_missing_dtu():
    """Test app configuration without DTU."""
    with pytest.raises(ValidationError):
        AppConfig()

