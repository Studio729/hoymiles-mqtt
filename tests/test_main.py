#!/usr/bin/env python
"""Tests for __main__ module."""

from unittest.mock import patch

from hoymiles_smiles.__main__ import main


def test_main_happy_path(monkeypatch):
    """Happy path verification for main() function."""
    monkeypatch.setattr('sys.argv', ['hoymiles_smiles', '--dtu-host', 'some_dtu_host'])
    with patch('hoymiles_smiles.__main__.run_periodic_coordinator') as mock_run_periodic:
        main()
    mock_run_periodic.assert_called_once()
