#!/usr/bin/env python3
"""
send_test_github_start_command.py

This script sends a command to the running DataSourceManager (listening on localhost:6379)
to start the GitHub data source (BBGitHubDataSource) with hardcoded parameters:
    - datasource: BBGitHubDataSource
    - username: PabloBorda
    - token: (empty)
    - target_directory: output/github

The DataSourceManager will execute the datasource_launcher.py script (located in the project root)
using the current Python interpreter. Output from the launched process will be streamed to the console.
The script waits for a response on a dedicated response channel and prints it.
"""

import json
import os
import socket
import sys
import time
import uuid
import redis
from brainboost_configuration_package.BBConfig import BBConfig

def get_local_ip():
    """Determine the local IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def main():
    # Hardcoded values for this test.
    datasource = "BBGitHubDataSource"
    username = "PabloBorda"
    token = ""
    target_directory = "output/github"

    # Build channel names.
    local_ip = get_local_ip()
    command_channel = f"datasource_commands_{local_ip}"
    response_channel = f"response_{uuid.uuid4().hex}"

    # Construct the command payload.
    command = {
        "request_id": str(uuid.uuid4()),
        "method": "start_data_source",
        "params": {
            "datasource": datasource,
            "params": {
                "username": username,
                "token": token,
                "target_directory": target_directory
            }
        },
        "response_channel": response_channel
    }

    # Connect to Redis.
    r = redis.Redis(host=BBConfig.get('redis_server_ip'), port=BBConfig.get('redis_server_port'), db=0, decode_responses=True)
    pubsub = r.pubsub()
    pubsub.subscribe(response_channel)

    print(f"Publishing command to channel '{command_channel}':")
    print(json.dumps(command, indent=2))
    r.publish(command_channel, json.dumps(command))

    # Wait up to 15 seconds for a response.
    timeout = time.time() + 15
    response = None
    while time.time() < timeout:
        message = pubsub.get_message(timeout=1)
        if message and message["type"] == "message":
            try:
                response = json.loads(message["data"])
            except Exception as e:
                print(f"Error parsing response JSON: {e}")
            break
        time.sleep(0.5)

    if response:
        print("Received response:")
        print(json.dumps(response, indent=2))
    else:
        print("No response received within the timeout period.")

if __name__ == "__main__":
    main()
