"""
Telnyx + LiveKit SIP Trunk Setup Script
========================================
This script automates the entire SIP trunk setup:
1. Creates a Credential Connection on Telnyx
2. Creates SIP credentials (username/password) for that connection
3. Associates your phone number with the connection
4. Creates an Outbound SIP Trunk in LiveKit
5. Prints the values you need to add to your .env file
"""

import asyncio
import os
import sys
import secrets
import string
import certifi
import requests

os.environ['SSL_CERT_FILE'] = certifi.where()

from dotenv import load_dotenv
from livekit import api
from livekit.protocol.sip import CreateSIPOutboundTrunkRequest, SIPOutboundTrunkInfo

load_dotenv(".env")

TELNYX_API_KEY = os.getenv("TELNYX_API_KEY")
TELNYX_BASE_URL = "https://api.telnyx.com/v2"
HEADERS = {
    "Authorization": f"Bearer {TELNYX_API_KEY}",
    "Content-Type": "application/json",
}

LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
OUTBOUND_NUMBER = os.getenv("TELNYX_OUTBOUND_NUMBER", "+13027750848")

# Derive the LiveKit SIP FQDN from the WebSocket URL
# wss://test-wpgr11p7.livekit.cloud -> test-wpgr11p7.sip.livekit.cloud
LIVEKIT_SIP_FQDN = LIVEKIT_URL.replace("wss://", "").replace(".livekit.cloud", ".sip.livekit.cloud")


def generate_password(length=20):
    """Generate a secure random password."""
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


def step1_create_credential_connection(sip_username, sip_password):
    """Create a Credential Connection on Telnyx with built-in auth credentials."""
    print("\n📡 Step 1: Creating Telnyx Credential Connection...")
    
    payload = {
        "connection_name": "LiveKit Voice Agent",
        "user_name": sip_username,
        "password": sip_password,
        "active": True,
        "anchorsite_override": "Latency",
        "dtmf_type": "RFC 2833",
        "webhook_api_version": "2",
        "inbound": {
            "ani_number_format": "E.164",
            "dnis_number_format": "e164",
            "codecs": ["G722", "G711U", "G711A"],
            "channel_limit": 10,
            "generate_ringback_tone": True,
        },
        "outbound": {
            "channel_limit": 10,
            "localization": "US",
        }
    }
    
    resp = requests.post(f"{TELNYX_BASE_URL}/credential_connections", headers=HEADERS, json=payload)
    
    if resp.status_code in [200, 201]:
        data = resp.json()["data"]
        connection_id = data["id"]
        print(f"   ✅ Connection created: {connection_id}")
        print(f"   Name: {data.get('connection_name', 'N/A')}")
        print(f"   SIP Username: {sip_username}")
        return connection_id
    else:
        print(f"   ❌ Failed: {resp.status_code}")
        print(f"   Response: {resp.text}")
        return None


# Step 2 removed - credentials are now part of the connection creation in Step 1


def step3_check_phone_number():
    """List phone numbers and check if our number exists."""
    print(f"\n📞 Step 3: Checking phone number {OUTBOUND_NUMBER}...")
    
    resp = requests.get(
        f"{TELNYX_BASE_URL}/phone_numbers",
        headers=HEADERS,
        params={"filter[phone_number]": OUTBOUND_NUMBER}
    )
    
    if resp.status_code == 200:
        data = resp.json()["data"]
        if data:
            phone = data[0]
            print(f"   ✅ Number found: {phone.get('phone_number', OUTBOUND_NUMBER)}")
            print(f"   Status: {phone.get('status', 'N/A')}")
            return phone.get("id")
        else:
            print(f"   ⚠️  Number {OUTBOUND_NUMBER} not found in your Telnyx account.")
            print(f"   You may need to purchase it from the Telnyx portal.")
            return None
    else:
        print(f"   ⚠️  Could not check numbers: {resp.status_code}")
        return None


def step4_assign_number_to_connection(phone_id, connection_id):
    """Assign the phone number to our credential connection."""
    if not phone_id:
        print("\n📱 Step 4: Skipping number assignment (no phone ID)")
        return
    
    print(f"\n📱 Step 4: Assigning number to connection...")
    
    payload = {
        "connection_id": connection_id,
    }
    
    resp = requests.patch(
        f"{TELNYX_BASE_URL}/phone_numbers/{phone_id}/voice",
        headers=HEADERS,
        json=payload
    )
    
    if resp.status_code == 200:
        print(f"   ✅ Number assigned to connection {connection_id}")
    else:
        print(f"   ⚠️  Could not assign: {resp.status_code} - {resp.text}")
        print(f"   You may need to do this manually in the Telnyx portal.")


async def step5_create_livekit_trunk(sip_username, sip_password):
    """Create the Outbound SIP Trunk in LiveKit."""
    print("\n🏗️  Step 5: Creating LiveKit Outbound SIP Trunk...")
    
    lkapi = api.LiveKitAPI(url=LIVEKIT_URL, api_key=LIVEKIT_API_KEY, api_secret=LIVEKIT_API_SECRET)
    
    try:
        trunk_info = SIPOutboundTrunkInfo(
            name="Telnyx Trunk",
            address="sip.telnyx.com",
            auth_username=sip_username,
            auth_password=sip_password,
            numbers=[OUTBOUND_NUMBER] if OUTBOUND_NUMBER else [],
        )
        
        request = CreateSIPOutboundTrunkRequest(trunk=trunk_info)
        trunk = await lkapi.sip.create_outbound_trunk(request)
        
        trunk_id = trunk.sip_trunk_id
        print(f"   ✅ LiveKit Trunk Created!")
        print(f"   Trunk ID: {trunk_id}")
        return trunk_id
        
    except Exception as e:
        print(f"   ❌ Failed to create LiveKit trunk: {e}")
        return None
    finally:
        await lkapi.aclose()


async def main():
    print("=" * 60)
    print("  🚀 Telnyx + LiveKit SIP Trunk Auto-Setup")
    print("=" * 60)
    
    # Validate required env vars
    if not TELNYX_API_KEY:
        print("❌ TELNYX_API_KEY not found in .env")
        return
    if not (LIVEKIT_URL and LIVEKIT_API_KEY and LIVEKIT_API_SECRET):
        print("❌ LiveKit credentials not found in .env")
        return
    
    print(f"\nLiveKit SIP FQDN: {LIVEKIT_SIP_FQDN}")
    print(f"Outbound Number: {OUTBOUND_NUMBER}")
    
    # Generate SIP credentials
    sip_username = f"livekitagent{secrets.token_hex(4)}"
    sip_password = generate_password()
    
    # Step 1: Create Telnyx Credential Connection (includes SIP credentials)
    connection_id = step1_create_credential_connection(sip_username, sip_password)
    if not connection_id:
        print("\n❌ Cannot continue without a connection. Exiting.")
        return
    
    # Step 2: Check phone number
    phone_id = step3_check_phone_number()
    
    # Step 3: Assign number to connection
    step4_assign_number_to_connection(phone_id, connection_id)
    
    # Step 5: Create LiveKit outbound trunk
    trunk_id = await step5_create_livekit_trunk(sip_username, sip_password)
    
    # Print summary
    print("\n" + "=" * 60)
    print("  📋 SETUP COMPLETE - Update Your .env File")
    print("=" * 60)
    print(f"""
Copy these values into your .env file:

TELNYX_SIP_TRUNK_ID={trunk_id or 'FAILED_CHECK_ABOVE'}
OUTBOUND_TRUNK_ID={trunk_id or 'FAILED_CHECK_ABOVE'}
TELNYX_SIP_DOMAIN=sip.telnyx.com
TELNYX_USERNAME={sip_username}
TELNYX_PASSWORD={sip_password}
TELNYX_OUTBOUND_NUMBER={OUTBOUND_NUMBER}
""")
    
    if trunk_id:
        print("✅ Everything is set up! After updating .env, run:")
        print("   python agent.py start")
    else:
        print("⚠️  Some steps failed. Check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())
