#!/usr/bin/env python3
"""
start_datasource_manager.py

This script initializes and runs the DataSourceManager.
It adjusts sys.path so that the package "brainboost_data_source_package" is always importable,
whether you run the script from the repository root or from within the package directory.
The DataSourceManager publishes its registration on the "manager_registry" channel
periodically (every 5 seconds), so that any client (e.g. a PyQt frontend) can eventually
receive its network connection information.
"""

import os
import sys
import redis
import json
import socket
import time
import threading
from brainboost_configuration_package.BBConfig import BBConfig
from brainboost_data_source_logger_package.BBLogger import BBLogger

# Determine the directory where this script resides.
script_dir = os.path.dirname(os.path.abspath(__file__))

# If the script's directory name is "brainboost_data_source_package", then we are inside the package folder.
# In that case, add its parent directory to sys.path so that the package is importable as a top-level module.
if os.path.basename(script_dir) == "brainboost_data_source_package":
    repo_root = os.path.abspath(os.path.join(script_dir, os.pardir))
else:
    # Otherwise, assume we're in the repository root.
    repo_root = script_dir

if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# Optional: Debug print to verify sys.path.
# print("sys.path:", sys.path)

# Now try to import the DataSourceManager.
try:
    from brainboost_data_source_package.data_source_manager.DataSourceManager import DataSourceManager
except ModuleNotFoundError as e:
    print("Import failed even after sys.path adjustment:", e)
    print("Make sure that an __init__.py file exists in the root of 'brainboost_data_source_package'")
    sys.exit(1)


def get_local_ip():
    """
    Returns the local IP address of the machine.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception as e:
        BBLogger.log(f"Error obtaining local IP address: {e}")
        ip = '127.0.0.1'
    return ip


def wait_for_redis(redis_host, redis_port, interval=30):
    """
    Wait until a connection to the Redis server at redis_host:redis_port is successful.
    On the first failure, a Telegram notification is sent.
    Subsequent logs during waiting are local only.
    Once connected, a Telegram notification is sent and the Redis client is returned.
    """
    # Attempt an initial connection
    try:
        redis_client = redis.Redis(host=redis_host, port=redis_port, db=0, socket_timeout=5)
        redis_client.ping()
        BBLogger.log(f"Connected to Redis at {redis_host}:{redis_port}", telegram=True)
        return redis_client
    except Exception as e:
        BBLogger.log(f"Waiting for Redis server to be available at: {redis_host}:{redis_port}", telegram=True)
    
    # Loop until connection is successful.
    while True:
        try:
            redis_client = redis.Redis(host=redis_host, port=redis_port, db=0, socket_timeout=5)
            redis_client.ping()
            BBLogger.log(f"Connected to Redis at {redis_host}:{redis_port}", telegram=True)
            return redis_client
        except Exception:
            BBLogger.log("Waiting for Redis server to be available", telegram=False)
            time.sleep(interval)


def main():
    local_ip = get_local_ip()
    BBLogger.log(f"Server Local IP address determined: {local_ip}", telegram=True)
    
    redis_host = BBConfig.get('brainboost_server_vm_redis_private_ip_0')
    redis_port = BBConfig.get('brainboost_server_vm_redis_private_port_0')
    
    # Wait for the Redis server to be available
    redis_client = wait_for_redis(redis_host, redis_port)
    
    command_channel = f"datasource_commands_{local_ip}"
    
    manager = DataSourceManager(command_channel=command_channel)
    
    manager_thread = threading.Thread(target=manager.start, daemon=True)
    manager_thread.start()
    BBLogger.log(f"DataSourceManager started and listening on channel: '{command_channel}'", telegram=True)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        BBLogger.log("Shutting down DataSourceManager...", telegram=True)
        sys.exit(0)


BBLogger.log('The current path is ' + str(sys.path))

if __name__ == "__main__":
    main()
