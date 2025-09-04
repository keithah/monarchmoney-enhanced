#!/usr/bin/env python3
"""
Manual test of the login flow step by step.
"""

import asyncio
import json
import os
import oathtool
from dotenv import load_dotenv
from aiohttp import ClientSession, FormData

load_dotenv()

async def manual_login_test():
    """Manually test login step by step."""
    
    email = os.getenv("MONARCH_EMAIL")
    password = os.getenv("MONARCH_PASSWORD")
    mfa_secret = os.getenv("MONARCH_MFA_SECRET")
    
    print(f"Testing with email: {email}")
    print(f"Password length: {len(password) if password else 'None'}")
    print(f"MFA secret length: {len(mfa_secret) if mfa_secret else 'None'}")
    
    # Generate TOTP code
    totp_code = oathtool.generate_otp(mfa_secret)
    print(f"Generated TOTP: {totp_code}")
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://app.monarchmoney.com",
        "Referer": "https://app.monarchmoney.com/",
    }
    
    login_url = "https://api.monarchmoney.com/auth/login/"
    
    async with ClientSession() as session:
        
        # Step 1: Try login without MFA to see MFA_REQUIRED response
        print("\n=== Step 1: Basic login (should get MFA_REQUIRED) ===")
        form_data = FormData()
        form_data.add_field("username", email)
        form_data.add_field("password", password)
        form_data.add_field("supports_mfa", "true")
        
        try:
            async with session.post(login_url, data=form_data, headers=headers) as response:
                print(f"Status: {response.status}")
                response_text = await response.text()
                print(f"Response: {response_text}")
        except Exception as e:
            print(f"Error: {e}")
        
        # Step 2: Try with MFA included in initial request
        print(f"\n=== Step 2: Login with MFA code {totp_code} ===")
        form_data = FormData()
        form_data.add_field("username", email)
        form_data.add_field("password", password)
        form_data.add_field("supports_mfa", "true")
        form_data.add_field("totp", totp_code)
        
        try:
            async with session.post(login_url, data=form_data, headers=headers) as response:
                print(f"Status: {response.status}")
                response_text = await response.text()
                print(f"Response: {response_text}")
        except Exception as e:
            print(f"Error: {e}")
        
        # Step 3: Try separate MFA submission
        print(f"\n=== Step 3: MFA submission style ===")
        form_data = FormData()
        form_data.add_field("username", email)
        form_data.add_field("password", password)
        form_data.add_field("code", totp_code)
        form_data.add_field("trusted_device", "true")
        
        try:
            async with session.post(login_url, data=form_data, headers=headers) as response:
                print(f"Status: {response.status}")
                response_text = await response.text()
                print(f"Response: {response_text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(manual_login_test())