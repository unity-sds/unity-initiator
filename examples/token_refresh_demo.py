#!/usr/bin/env python3
"""
Demonstration script showing automatic token refresh functionality.

This script simulates a long-running application that makes multiple API calls
and shows how tokens are automatically refreshed when they expire.

Usage:
    python token_refresh_demo.py
"""

import os
import time
import logging
from unity_initiator.utils.auth_utils import TokenManager

# Enable debug logging to see token refresh in action
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def simulate_api_call(token, call_number):
    """Simulate an API call using the provided token."""
    print(f"🔌 API Call #{call_number}: Using token {token[:20]}...")
    # In a real application, you would use this token for your API calls
    time.sleep(1)  # Simulate API call duration

def main():
    """Demonstrate automatic token refresh."""
    
    # Check if required environment variables are set
    unity_user = os.getenv("UNITY_USER")
    unity_password = os.getenv("UNITY_PASSWORD")
    unity_client_id = os.getenv("UNITY_CLIENT_ID")
    
    if not all([unity_user, unity_password, unity_client_id]):
        print("❌ Error: Please set the following environment variables:")
        print("   UNITY_USER, UNITY_PASSWORD, UNITY_CLIENT_ID")
        print("\nExample:")
        print("   export UNITY_USER='your-username'")
        print("   export UNITY_PASSWORD='your-password'")
        print("   export UNITY_CLIENT_ID='your-client-id'")
        return 1
    
    print("🚀 Starting Token Refresh Demonstration")
    print("=" * 50)
    
    # Create a token manager
    print("📋 Creating TokenManager...")
    manager = TokenManager(
        username=unity_user,
        password=unity_password,
        client_id=unity_client_id,
        region="us-west-2"
    )
    
    print("✅ TokenManager created successfully")
    print("\n🔄 Simulating long-running application with multiple API calls...")
    print("   (Tokens will be automatically refreshed when needed)")
    print("-" * 50)
    
    # Simulate multiple API calls over time
    for i in range(1, 11):
        print(f"\n📞 Making API call #{i}...")
        
        # Get a valid token (this will automatically refresh if needed)
        token = manager.get_valid_token()
        
        if token:
            simulate_api_call(token, i)
            print(f"✅ API call #{i} completed successfully")
        else:
            print(f"❌ Failed to get valid token for API call #{i}")
            return 1
        
        # Wait between calls to simulate real application behavior
        if i < 10:  # Don't wait after the last call
            print("⏳ Waiting 30 seconds before next call...")
            time.sleep(30)
    
    print("\n" + "=" * 50)
    print("🎉 Demonstration completed successfully!")
    print("\n📊 Summary:")
    print("   - Made 10 API calls")
    print("   - Tokens were automatically managed")
    print("   - No manual token refresh required")
    print("   - Application ran seamlessly")
    
    return 0

if __name__ == "__main__":
    exit(main()) 