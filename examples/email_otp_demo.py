#!/usr/bin/env python3
"""
Interactive Email OTP Demo for Monarch Money Enhanced

This example demonstrates how to handle email OTP codes that Monarch Money
sends during login. The library automatically detects 6-digit email codes
and handles them appropriately.

Usage:
    python3 examples/email_otp_demo.py

Requirements:
    - Your Monarch Money email and password
    - Access to the email account to receive OTP codes
"""

import asyncio
import getpass
import sys
from monarchmoney import MonarchMoney


async def interactive_email_otp_demo():
    """
    Interactive demonstration of email OTP login flow.
    """
    print("🔐 Monarch Money Enhanced - Email OTP Demo")
    print("=" * 50)
    print()

    # Get credentials interactively
    try:
        email = input("📧 Enter your Monarch Money email: ").strip()
        if not email:
            print("❌ Email is required")
            return False

        password = getpass.getpass("🔑 Enter your password: ")
        if not password:
            print("❌ Password is required")
            return False

    except KeyboardInterrupt:
        print("\n👋 Cancelled by user")
        return False

    print(f"\n🚀 Attempting login for: {email}")
    print("📬 If Monarch Money sends an email code, you'll be prompted to enter it...")

    mm = MonarchMoney()

    try:
        # Attempt initial login
        await mm.login(
            email=email,
            password=password,
            use_saved_session=False,  # Force fresh login to test email OTP
            save_session=False        # Don't save session for demo
        )

        print("✅ Login successful without additional verification!")

    except Exception as e:
        error_msg = str(e).lower()

        # Check if this looks like an MFA/email OTP requirement
        if any(keyword in error_msg for keyword in [
            'mfa', 'multi-factor', 'verification', 'code', 'otp', 'email'
        ]):
            print("\n📧 Email verification required!")
            print("🔍 Check your email for a verification code from Monarch Money")
            print("   (Subject: 'Your code is ...' or similar)")
            print()

            try:
                # Get the email OTP code from user
                email_code = input("🔢 Enter the 6-digit code from your email: ").strip()

                if not email_code:
                    print("❌ Code is required")
                    return False

                if not (email_code.isdigit() and len(email_code) == 6):
                    print("⚠️  Warning: Expected 6-digit numeric code")
                    print("   Proceeding anyway in case it's a different format...")

                print(f"\n🔐 Submitting email verification code: {email_code}")

                # Use the multi_factor_authenticate method with the email code
                await mm.multi_factor_authenticate(email, password, email_code)

                print("✅ Email OTP verification successful!")

            except KeyboardInterrupt:
                print("\n👋 Cancelled by user")
                return False
            except Exception as mfa_error:
                print(f"❌ Email OTP verification failed: {mfa_error}")
                print("\n💡 Troubleshooting tips:")
                print("   - Make sure you entered the code correctly")
                print("   - Check if the code has expired (usually valid for a few minutes)")
                print("   - Try requesting a new code by logging in again")
                return False
        else:
            print(f"❌ Login failed: {e}")
            print("\n💡 This might not be an email OTP issue. Common problems:")
            print("   - Incorrect email or password")
            print("   - Network connectivity issues")
            print("   - Monarch Money service issues")
            return False

    # Test basic functionality
    print("\n🧪 Testing basic API functionality...")
    try:
        accounts = await mm.get_accounts()
        print(f"✅ Successfully retrieved {len(accounts)} accounts")

        if accounts:
            print("\n📊 Account summary:")
            for i, account in enumerate(accounts[:3], 1):  # Show first 3 accounts
                name = account.get('name', 'Unknown')
                balance = account.get('currentBalance', 0)
                print(f"   {i}. {name}: ${balance:,.2f}")
            if len(accounts) > 3:
                print(f"   ... and {len(accounts) - 3} more accounts")

    except Exception as e:
        print(f"⚠️  Basic API test failed: {e}")
        print("   Login succeeded but API calls are having issues")

    print("\n🎉 Email OTP demo completed successfully!")
    print("\n📚 Key takeaways:")
    print("   - The library automatically detects 6-digit email codes")
    print("   - Email codes use the 'email_otp' field internally")
    print("   - TOTP codes from authenticator apps use the 'totp' field")
    print("   - Both are handled transparently by the library")

    return True


def main():
    """Main function to run the interactive demo."""
    print("Starting Email OTP Demo...\n")

    try:
        success = asyncio.run(interactive_email_otp_demo())
        if success:
            print("\n✅ Demo completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Demo failed or was cancelled")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n👋 Demo cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        print("Please report this issue at: https://github.com/keithah/monarchmoney-enhanced/issues")
        sys.exit(1)


if __name__ == "__main__":
    main()