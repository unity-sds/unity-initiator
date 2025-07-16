#!/usr/bin/env python3
"""
OAuth2 Token Initialization Script

This script helps initialize OAuth2 tokens for proxy authentication.
It handles the OAuth2 authorization code flow and stores tokens for use
by the Unity Initiator.

Usage:
    python oauth2_token_init.py --help
"""

import argparse
import json
import sys

from unity_initiator.utils.oauth2_utils import (
    OAuth2Manager,
    extract_authorization_code_from_url,
)


def main():
    """Main function to handle OAuth2 token initialization."""
    parser = argparse.ArgumentParser(
        description="Initialize OAuth2 tokens for proxy authentication"
    )
    parser.add_argument(
        "--cognito-domain",
        required=True,
        help="Cognito domain (e.g., 'unitysds.auth.us-west-2.amazoncognito.com')",
    )
    parser.add_argument("--client-id", required=True, help="OAuth2 client ID")
    parser.add_argument(
        "--redirect-uri", required=True, help="Redirect URI configured in Cognito"
    )
    parser.add_argument(
        "--scope", default="openid email profile", help="OAuth2 scopes to request"
    )
    parser.add_argument("--region", default="us-west-2", help="AWS region")
    parser.add_argument(
        "--callback-url",
        help="OAuth2 callback URL with authorization code (if you have it)",
    )
    parser.add_argument(
        "--output-file",
        help="File to save token information (default: oauth2_tokens.json)",
    )

    args = parser.parse_args()

    # Initialize OAuth2 manager
    oauth2_manager = OAuth2Manager(
        cognito_domain=args.cognito_domain,
        client_id=args.client_id,
        redirect_uri=args.redirect_uri,
        scope=args.scope,
        region=args.region,
    )

    # If callback URL is provided, extract code and exchange for token
    if args.callback_url:
        print("Extracting authorization code from callback URL...")
        auth_code = extract_authorization_code_from_url(args.callback_url)

        if not auth_code:
            print("Error: No authorization code found in callback URL")
            sys.exit(1)

        print("Exchanging authorization code for token...")
        try:
            token_data = oauth2_manager.exchange_code_for_token(auth_code)
            print("✅ Successfully obtained OAuth2 tokens!")

            # Save token information
            output_file = args.output_file or "oauth2_tokens.json"
            token_info = {
                "access_token": token_data.get("access_token"),
                "refresh_token": token_data.get("refresh_token"),
                "expires_in": token_data.get("expires_in"),
                "token_type": token_data.get("token_type"),
                "scope": token_data.get("scope"),
                "oauth2_config": {
                    "cognito_domain": args.cognito_domain,
                    "client_id": args.client_id,
                    "redirect_uri": args.redirect_uri,
                    "scope": args.scope,
                    "region": args.region,
                },
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(token_info, f, indent=2)

            print(f"✅ Token information saved to {output_file}")
            print(
                f"Access token expires in: {token_data.get('expires_in', 'unknown')} seconds"
            )

        except Exception as e:
            print(f"❌ Error exchanging code for token: {str(e)}")
            sys.exit(1)

    else:
        # Generate authorization URL for manual flow
        print("Generating OAuth2 authorization URL...")
        auth_url = oauth2_manager.get_authorization_url()

        print("\n" + "=" * 80)
        print("OAUTH2 AUTHORIZATION FLOW")
        print("=" * 80)
        print("\n1. Open this URL in your browser:")
        print(f"   {auth_url}")
        print("\n2. Complete the authentication flow")
        print("\n3. Copy the callback URL from your browser")
        print("\n4. Run this script again with the --callback-url parameter:")
        print(
            f"   python {sys.argv[0]} --cognito-domain {args.cognito_domain} "
            f"--client-id {args.client_id} --redirect-uri '{args.redirect_uri}' "
            f"--callback-url 'YOUR_CALLBACK_URL'"
        )
        print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
