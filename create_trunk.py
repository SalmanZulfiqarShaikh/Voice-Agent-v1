import asyncio
import os
import certifi

# Fix SSL
os.environ['SSL_CERT_FILE'] = certifi.where()

from dotenv import load_dotenv
from livekit import api
from livekit.protocol.sip import CreateSIPOutboundTrunkRequest, SIPOutboundTrunkInfo

load_dotenv(".env")

async def main():
    print("Connecting to LiveKit API...")
    url = os.getenv("LIVEKIT_URL")
    key = os.getenv("LIVEKIT_API_KEY")
    secret = os.getenv("LIVEKIT_API_SECRET")

    # Telnyx SIP Credentials
    sip_address = os.getenv("TELNYX_SIP_DOMAIN", "sip.telnyx.com")
    username = os.getenv("TELNYX_USERNAME")
    password = os.getenv("TELNYX_PASSWORD")
    number = os.getenv("TELNYX_OUTBOUND_NUMBER")

    if not (url and key and secret):
        print("Error: Missing LiveKit credentials")
        return

    if not (sip_address and username and password):
        print("Error: Missing SIP credentials (TELNYX_SIP_DOMAIN, TELNYX_USERNAME, TELNYX_PASSWORD)")
        return

    lkapi = api.LiveKitAPI(url=url, api_key=key, api_secret=secret)

    try:
        print(f"Creating SIP Trunk for {sip_address}...")
        
        trunk_info = SIPOutboundTrunkInfo(
            name="Telnyx Trunk",
            address=sip_address,
            auth_username=username,
            auth_password=password,
            numbers=[number] if number else [],
        )

        request = CreateSIPOutboundTrunkRequest(trunk=trunk_info)
        
        trunk = await lkapi.sip.create_outbound_trunk(request)
        
        print("\n✅ SIP Trunk Created Successfully!")
        print(f"Trunk ID: {trunk.sip_trunk_id}")
        print(f"Name: {trunk.name}")
        print(f"Numbers: {trunk.numbers}")
        print(f"\n📋 Copy this Trunk ID into your .env file:")
        print(f"   TELNYX_SIP_TRUNK_ID={trunk.sip_trunk_id}")
        print(f"   OUTBOUND_TRUNK_ID={trunk.sip_trunk_id}")
        
    except Exception as e:
        print(f"\n❌ Error creating trunk: {e}")
    finally:
        await lkapi.aclose()

if __name__ == "__main__":
    asyncio.run(main())
