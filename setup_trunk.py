import asyncio
import os
import certifi

# Fix SSL
os.environ['SSL_CERT_FILE'] = certifi.where()

from dotenv import load_dotenv
from livekit import api

# Load environment variables
load_dotenv(".env")

async def main():
    # Initialize LiveKit API
    lkapi = api.LiveKitAPI()
    sip = lkapi.sip
    
    trunk_id = os.getenv("OUTBOUND_TRUNK_ID")
    address = os.getenv("TELNYX_SIP_DOMAIN", "sip.telnyx.com")
    username = os.getenv("TELNYX_USERNAME")
    password = os.getenv("TELNYX_PASSWORD")
    number = os.getenv("TELNYX_OUTBOUND_NUMBER")
    
    if not trunk_id:
        print("Error: OUTBOUND_TRUNK_ID not found in .env")
        return

    print(f"Updating SIP Trunk: {trunk_id}")
    print(f"  Address: {address}")
    print(f"  Username: {username}")
    print(f"  Numbers: [{number}]")

    try:
        # Update the trunk with the correct credentials and settings
        await sip.update_outbound_trunk_fields(
            trunk_id,
            address=address,
            auth_username=username,
            auth_password=password,
            numbers=[number] if number else [],
        )
        print("\n✅ SIP Trunk updated successfully!")
        
    except Exception as e:
        print(f"\n❌ Failed to update trunk: {e}")
    finally:
        await lkapi.aclose()

if __name__ == "__main__":
    asyncio.run(main())
