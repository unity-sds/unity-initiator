#!/usr/bin/env python3
"""
Example script demonstrating how to use SubmitDagByID with Cognito authentication.

This script shows how to submit a DAG run to Airflow using either:
1. Direct Bearer token authentication
2. Cognito token fetching with Unity credentials
3. Basic authentication (legacy)

Usage:
    python submit_dag_with_cognito.py --help
"""

import argparse
import os
from unity_initiator.actions.submit_dag_by_id import SubmitDagByID


def main():
    parser = argparse.ArgumentParser(
        description="Submit a DAG run to Airflow with various authentication methods"
    )
    parser.add_argument(
        "--airflow-endpoint",
        required=True,
        help="Base URL for the Airflow API endpoint"
    )
    parser.add_argument(
        "--dag-id",
        required=True,
        help="ID of the DAG to trigger"
    )
    parser.add_argument(
        "--payload",
        default='{"example": "data"}',
        help="JSON payload for the DAG run"
    )
    
    # Authentication options
    auth_group = parser.add_mutually_exclusive_group(required=True)
    auth_group.add_argument(
        "--token",
        help="Direct Bearer token for authentication"
    )
    auth_group.add_argument(
        "--cognito",
        action="store_true",
        help="Use Cognito authentication (requires UNITY_USER, UNITY_PASSWORD, UNITY_CLIENT_ID env vars)"
    )
    auth_group.add_argument(
        "--basic",
        action="store_true",
        help="Use basic authentication (requires AIRFLOW_USERNAME, AIRFLOW_PASSWORD env vars)"
    )
    
    # Optional parameters
    parser.add_argument(
        "--on-success",
        help="Success callback URL"
    )
    parser.add_argument(
        "--unity-region",
        default="us-west-2",
        help="AWS region for Cognito (default: us-west-2)"
    )
    
    args = parser.parse_args()
    
    # Prepare parameters based on authentication method
    params = {
        "airflow_base_api_endpoint": args.airflow_endpoint,
        "dag_id": args.dag_id,
    }
    
    if args.on_success:
        params["on_success"] = args.on_success
    
    if args.token:
        # Direct token authentication
        params["airflow_token"] = args.token
        print("Using direct Bearer token authentication")
        
    elif args.cognito:
        # Cognito authentication
        unity_user = os.getenv("UNITY_USER")
        unity_password = os.getenv("UNITY_PASSWORD")
        unity_client_id = os.getenv("UNITY_CLIENT_ID")
        
        if not all([unity_user, unity_password, unity_client_id]):
            print("Error: UNITY_USER, UNITY_PASSWORD, and UNITY_CLIENT_ID environment variables are required for Cognito authentication")
            return 1
        
        params.update({
            "unity_username": unity_user,
            "unity_password": unity_password,
            "unity_client_id": unity_client_id,
            "unity_region": args.unity_region
        })
        print("Using Cognito authentication")
        
    elif args.basic:
        # Basic authentication
        airflow_username = os.getenv("AIRFLOW_USERNAME")
        airflow_password = os.getenv("AIRFLOW_PASSWORD")
        
        if not all([airflow_username, airflow_password]):
            print("Error: AIRFLOW_USERNAME and AIRFLOW_PASSWORD environment variables are required for basic authentication")
            return 1
        
        params.update({
            "airflow_username": airflow_username,
            "airflow_password": airflow_password
        })
        print("Using basic authentication")
    
    # Prepare payload
    import json
    try:
        payload = json.loads(args.payload)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON payload: {args.payload}")
        return 1
    
    payload_info = {
        "source": "unity-initiator-example",
        "timestamp": "2024-01-01T00:00:00Z"
    }
    
    # Submit the DAG
    print(f"Submitting DAG {args.dag_id} to {args.airflow_endpoint}")
    
    action = SubmitDagByID(payload, payload_info, params)
    result = action.execute()
    
    if result["success"]:
        print("✅ DAG submitted successfully!")
        print(f"Response: {result['response']}")
        return 0
    else:
        print("❌ Failed to submit DAG")
        print(f"Error: {result['response']}")
        return 1


if __name__ == "__main__":
    exit(main()) 