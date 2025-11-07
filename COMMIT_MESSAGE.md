# Commit Message

## fix: Complete test fixes for InfluxDB and MySQL/MariaDB support

### Changes

**tests/test_persistence.py:**
- Improved mock setup for database initialization tests
- Added complete mock connection and cursor objects
- Added all 6 schema tables to mock return values
- Ensures _create_schema() method works with mocked objects

**tests/test_config.py:**
- Added comprehensive tests for InfluxDBConfig
- Added tests for DatabaseConfig with PostgreSQL/MySQL/MariaDB
- Tests URL validation for InfluxDB
- Tests database type normalization

### Why This Fix Is Needed

The previous mocks were incomplete - they didn't properly mock the connection
and cursor objects that _create_schema() uses. This caused the initialization
to fail when trying to execute SQL statements.

The new mocks:
1. Create proper mock connection with cursor() method
2. Return all 6 required schema tables
3. Mock all adapter methods used during initialization
4. Allow schema creation to complete without errors

### Testing

All tests now pass:
```bash
pytest tests/ -v
tox -e py312
tox -e py313
```

### Related

- Fixes GitHub Actions build failure
- Completes InfluxDB v3 integration
- Completes MySQL/MariaDB database support

