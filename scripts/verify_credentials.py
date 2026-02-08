import boto3
import botocore.utils
import datetime
import os
from dateutil.tz import tzutc
from unittest.mock import patch

# Credentials provided by user
ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")

def verify_credentials():
    print("Verifying credentials...")
    
    # Create a session
    session = boto3.Session(
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        region_name="us-east-1"
    )

    # 1. Attempt basic call to see if it works or fails with expected skew
    sts = session.client('sts')
    try:
        print("Attempting standard connection...")
        identity = sts.get_caller_identity()
        print(f"✅ Success! User ARN: {identity['Arn']}")
        return
    except Exception as e:
        print(f"⚠️ Standard connection failed: {e}")
        error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', '')
        if 'SignatureDoesNotMatch' in str(e) or 'AuthFailure' in str(e) or 'InvalidClientTokenId' in str(e):
             if 'Signature not yet current' in str(e):
                 print("   -> Detected 'Signature not yet current'. Applying time correction...")
             else:
                 print("   -> Authentication failed. Trying with time correction anyway in case of clock skew...")

    
    print("\nAttempting with REFINED time correction (-5 hours 15 minutes)...")
    
    # We need to import datetime inside to patch it or patch the module botocore uses
    import botocore.auth
    
    original_utcnow = datetime.datetime.utcnow

    class MockDatetime(datetime.datetime):
        @classmethod
        def utcnow(cls):
            # Return time 5 hours and 15 minutes ago to match AWS
            new_time = original_utcnow() - datetime.timedelta(hours=5, minutes=15)
            return new_time

    # Patch botocore.auth.datetime instead of just datetime.datetime
    # botocore.auth imports datetime module, so we patch datetime.datetime inside it? 
    # Actually botocore.auth uses 'datetime.datetime.utcnow'.
    # So we patch botocore.auth.datetime.
    
    with patch('botocore.auth.datetime', MockDatetime):
        print(f"   (Debug) Patched time check: {botocore.auth.datetime.utcnow()}")
        try:
            # We need to re-create client/session inside patch or ensure signing happens here
            # For simplicity, we'll use a new client
            sts_corrected = session.client('sts')
            
            # Monkey-patching might be tricky if the library imports datetime directly.
            # Let's try to use botocore event system to adjust the date header? 
            # Actually, `datetime.datetime.utcnow` is used in `botocore.auth`.
            
            identity = sts_corrected.get_caller_identity()
            print(f"✅ Success with time correction! Credentials are VALID.")
            print(f"   User ARN: {identity['Arn']}")
            print(f"   Account: {identity['Account']}")
        except Exception as e:
            print(f"❌ Failed even with time correction: {e}")
            if 'InvalidAccessKeyId' in str(e):
                print("   -> The Access Key ID does not exist.")
            elif 'SignatureDoesNotMatch' in str(e):
                print("   -> The Secret Key might be incorrect.")

if __name__ == "__main__":
    verify_credentials()
