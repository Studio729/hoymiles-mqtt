#!/usr/bin/env python3
"""Script to check InfluxDB v3 data."""

from influxdb_client_3 import InfluxDBClient3

# Your InfluxDB configuration
HOST = "https://influxdb3.suttonclan.org"
TOKEN = "apiv3_hON1-RyMEHu7B8EqUUniMr2V8F9S7tlkI2p0Z-LlKs65vcq8RfBvIZlQ_UI00jYB8n5XocgIDhAPTpjTAqvg6Q"
DATABASE = "hoymiles"

print(f"Connecting to: {HOST}")
print(f"Database: {DATABASE}")
print("-" * 60)

try:
    # Create client
    client = InfluxDBClient3(
        host=HOST,
        token=TOKEN,
        database=DATABASE,
    )
    
    print("✓ Connection successful!")
    print()
    
    # Query 1: Check for ANY data in the database
    print("Query 1: Checking for any measurements...")
    query = """
    SHOW TABLES
    """
    try:
        result = client.query(query)
        if result:
            print(f"✓ Found measurements:")
            for row in result:
                print(f"  - {row}")
        else:
            print("✗ No measurements found")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print()
    
    # Query 2: Check DTU data (last 1 hour)
    print("Query 2: Checking DTU measurements (last 1 hour)...")
    query = """
    SELECT time, dtu_name, pv_power, today_production
    FROM dtu
    WHERE time > now() - interval '1 hour'
    ORDER BY time DESC
    LIMIT 10
    """
    try:
        result = client.query(query)
        table = result.to_pandas() if result else None
        if table is not None and not table.empty:
            print(f"✓ Found {len(table)} DTU records:")
            print(table)
        else:
            print("✗ No DTU data in last hour")
    except Exception as e:
        print(f"✗ Error querying DTU: {e}")
    
    print()
    
    # Query 3: Check inverter data
    print("Query 3: Checking inverter measurements (last 1 hour)...")
    query = """
    SELECT time, serial_number, temperature, grid_voltage
    FROM inverter
    WHERE time > now() - interval '1 hour'
    ORDER BY time DESC
    LIMIT 10
    """
    try:
        result = client.query(query)
        table = result.to_pandas() if result else None
        if table is not None and not table.empty:
            print(f"✓ Found {len(table)} inverter records:")
            print(table)
        else:
            print("✗ No inverter data in last hour")
    except Exception as e:
        print(f"✗ Error querying inverter: {e}")
    
    print()
    
    # Query 4: Check port data
    print("Query 4: Checking port measurements (last 1 hour)...")
    query = """
    SELECT time, serial_number, port_number, pv_power
    FROM port
    WHERE time > now() - interval '1 hour'
    ORDER BY time DESC
    LIMIT 10
    """
    try:
        result = client.query(query)
        table = result.to_pandas() if result else None
        if table is not None and not table.empty:
            print(f"✓ Found {len(table)} port records:")
            print(table)
        else:
            print("✗ No port data in last hour")
    except Exception as e:
        print(f"✗ Error querying port: {e}")
    
    print()
    
    # Query 5: Check ALL data (any time)
    print("Query 5: Checking for ANY data ever written...")
    for measurement in ['dtu', 'inverter', 'port']:
        query = f"""
        SELECT COUNT(*) as count
        FROM {measurement}
        """
        try:
            result = client.query(query)
            table = result.to_pandas() if result else None
            if table is not None and not table.empty:
                count = table['count'].iloc[0]
                print(f"  {measurement}: {count} total records")
            else:
                print(f"  {measurement}: 0 records")
        except Exception as e:
            print(f"  {measurement}: Error - {e}")
    
    print()
    print("=" * 60)
    print("TROUBLESHOOTING TIPS:")
    print("=" * 60)
    print()
    print("If no data found:")
    print("1. Check container logs: docker logs hoymiles-smiles")
    print("2. Verify INFLUXDB_ENABLED=true in your .env")
    print("3. Ensure DTU is actively producing data (daylight hours)")
    print("4. Check for errors: docker logs hoymiles-smiles | grep -i error")
    print("5. Verify token permissions in InfluxDB")
    print()
    
    client.close()
    
except Exception as e:
    print(f"✗ Connection failed: {e}")
    print()
    print("TROUBLESHOOTING:")
    print("1. Verify host URL is correct")
    print("2. Check token is valid and not expired")
    print("3. Ensure network connectivity: curl https://influxdb3.suttonclan.org")
    print("4. Verify database name exists in InfluxDB")

