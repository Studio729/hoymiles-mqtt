"""Tests for persistence module."""

import pytest
from unittest.mock import MagicMock, patch

from hoymiles_smiles.persistence import PersistenceManager


def test_persistence_initialization_disabled():
    """Test persistence manager initialization when disabled."""
    pm = PersistenceManager(enabled=False)
    assert pm.enabled is False
    assert pm.connection_pool is None


def test_persistence_initialization_postgres():
    """Test persistence manager initialization with PostgreSQL."""
    # Mock the adapter to avoid needing real database
    with patch('hoymiles_smiles.db_adapter.DatabaseAdapter') as mock_adapter:
        # Create mock connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Setup adapter mocks
        mock_adapter.return_value.create_pool = MagicMock(return_value=MagicMock())
        mock_adapter.return_value.get_schema_sql = MagicMock(return_value={
            'inverters': 'CREATE TABLE inverters ...',
            'inverter_data': 'CREATE TABLE inverter_data ...',
            'port_data': 'CREATE TABLE port_data ...',
            'production_cache': 'CREATE TABLE production_cache ...',
            'config_cache': 'CREATE TABLE config_cache ...',
            'system_metrics': 'CREATE TABLE system_metrics ...',
        })
        mock_adapter.return_value.get_connection = MagicMock(return_value=mock_conn)
        mock_adapter.return_value.get_cursor = MagicMock(return_value=mock_cursor)
        mock_adapter.return_value.return_connection = MagicMock()
        
        pm = PersistenceManager(
            enabled=True,
            type='postgres',
            host='localhost',
            port=5432,
            database='test',
            user='test',
            password='test',
        )
        
        assert pm.enabled is True
        assert pm.db_type == 'postgres'


def test_persistence_initialization_mysql():
    """Test persistence manager initialization with MySQL."""
    # Mock the adapter to avoid needing real database
    with patch('hoymiles_smiles.db_adapter.DatabaseAdapter') as mock_adapter:
        # Create mock connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Setup adapter mocks
        mock_adapter.return_value.create_pool = MagicMock(return_value=MagicMock())
        mock_adapter.return_value.get_schema_sql = MagicMock(return_value={
            'inverters': 'CREATE TABLE inverters ...',
            'inverter_data': 'CREATE TABLE inverter_data ...',
            'port_data': 'CREATE TABLE port_data ...',
            'production_cache': 'CREATE TABLE production_cache ...',
            'config_cache': 'CREATE TABLE config_cache ...',
            'system_metrics': 'CREATE TABLE system_metrics ...',
        })
        mock_adapter.return_value.get_connection = MagicMock(return_value=mock_conn)
        mock_adapter.return_value.get_cursor = MagicMock(return_value=mock_cursor)
        mock_adapter.return_value.return_connection = MagicMock()
        
        pm = PersistenceManager(
            enabled=True,
            type='mysql',
            host='192.168.1.50',
            port=3306,
            database='test',
            user='test',
            password='test',
        )
        
        assert pm.enabled is True
        assert pm.db_type == 'mysql'


def test_disabled_persistence_operations():
    """Test that operations don't fail when persistence is disabled."""
    pm = PersistenceManager(enabled=False)
    
    # These should not raise exceptions
    pm.save_production_cache("SN12345", 1, 1000, 50000)
    cache = pm.load_production_cache()
    assert len(cache) == 0
    
    pm.save_inverter_data("SN12345", "DTU", {})
    pm.save_port_data("SN12345", 1, {})
    pm.save_config("key", "value")
    pm.save_metric("power", 1500.0)
    
    pm.close()  # Should not fail

