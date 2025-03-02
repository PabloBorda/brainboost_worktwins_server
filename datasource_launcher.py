#!/usr/bin/env python3
import json
import sys
import os
import redis
from importlib import import_module
import argparse
from brainboost_data_source_logger_package.BBLogger import BBLogger
from brainboost_configuration_package.BBConfig import BBConfig

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--datasource", required=True)
    parser.add_argument("--params", required=True)
    # NEW: Accept client IP and port to send progress updates to the client’s Redis
    parser.add_argument("--client_ip", required=False, default=BBConfig.get('redis_server_ip'))
    parser.add_argument("--client_port", required=False, default=BBConfig.get('redis_server_port'), type=int)
    args = parser.parse_args()
    
    ds_class_name = args.datasource
    params = json.loads(args.params)
    
    # Log the client connection parameters.
    BBLogger.log("DatasourceLauncher: Using client Redis at {}:{}".format(args.client_ip, args.client_port))
    
    # Initialize a Redis client for publishing progress updates to the client's Redis instance.
    redis_client = redis.Redis(host=args.client_ip, port=args.client_port, db=0)

    # Define a progress callback that publishes progress messages.
    def progress_callback(name, total, processed, estimated_time):
        progress = int((processed / total) * 100) if total > 0 else 0
        message = {
            "pid": os.getpid(),
            "name": name,
            "total": total,
            "processed": processed,
            "progress": progress,
            "estimated_time": estimated_time
        }
        # Publish on the "datasource_progress" channel
        redis_client.publish("datasource_progress", json.dumps(message))
        BBLogger.log('Progress send to client: ' + json.dumps(message))
    
    # Dynamically import the requested data source class.
    module = import_module("brainboost_data_source_package.data_source_addons." + ds_class_name)
    ds_class = getattr(module, ds_class_name)
    
    ds_instance = ds_class(params=params)
    ds_instance.set_progress_callback(progress_callback)
    
    # Start the fetch process (which should call the progress callback periodically).
    ds_instance.fetch()

if __name__ == "__main__":
    main()
