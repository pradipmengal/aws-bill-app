import sys
import datetime
import time
import urllib.request
import os
from unittest.mock import patch

# Credentials
ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")

def get_real_aws_time():
    """Fetches the Date header from an AWS endpoint to get real server time."""
    try:
        # Use a public AWS endpoint that returns a Date header
        url = "https://aws.amazon.com"
        with urllib.request.urlopen(url) as response:
            date_str = response.headers['Date']
            # Parse Date: Sun, 08 Feb 2026 17:48:00 GMT
            # We need to parse this manually or use email.utils
            from email.utils import parsedate_to_datetime
            aws_time = parsedate_to_datetime(date_str)
            # Make sure it's offset-naive UTC for comparison if needed, or keep as is
            return aws_time.replace(tzinfo=None) # simplistic, assuming parsing gave us UTC-like
    except Exception as e:
        print(f"Failed to fetch AWS time: {e}")
        return None

def verify_with_offset():
    print("--- Advanced Credential Verification ---")
    
    # 1. Calculate Offset
    print("1. Calculating Time Offset...")
    system_time = datetime.datetime.utcnow()
    aws_time = get_real_aws_time()
    
    if not aws_time:
        print("Could not determine AWS time. Using hardcoded offset estimate.")
        # Fallback to previous estimate
        aws_time = system_time - datetime.timedelta(hours=5, minutes=15)
        
    offset = system_time - aws_time
    print(f"   System Time (UTC): {system_time}")
    print(f"   AWS Time (approx): {aws_time}")
    print(f"   Calculated Offset: {offset}")
    
    # 2. Define Patches
    # We need to shift "now" back by `offset`.
    
    class MockDatetime(datetime.datetime):
        @classmethod
        def utcnow(cls):
            return datetime.datetime.fromtimestamp(time.time() - offset.total_seconds()).utcfromtimestamp(time.time() - offset.total_seconds())
            # simpler:
            real_now = super().utcnow()
            return real_now - offset

        @classmethod
        def now(cls, tz=None):
            real_now = super().now(tz)
            return real_now - offset

    # We also need to patch time.time() because boto might use it for epoch
    original_time = time.time
    def mock_time():
        return original_time() - offset.total_seconds()
        
    # 3. Apply Patches BEFORE importing boto3 (if possible, but we import inside)
    # Since we already imported standard libs, we patch them.
    
    print("2. applying Patches and Connecting...")
    
    # Patching datetime.datetime is hard because it's a C extension type.
    # We have to patch it where it is imported or used.
    # But patching 'time.time' is easier.
    
    with patch('time.time', side_effect=mock_time):
        with patch('datetime.datetime', MockDatetime):
            # We also need to patch botocore's usage of datetime if it imported it directly
            # It usually does: from datetime import datetime
            
            # IMPORTS INSIDE PATCH BLOCK
            import boto3
            import botocore.auth
            import botocore.utils
            
            # Manually patch botocore's datetime reference if it exists
            if hasattr(botocore.auth, 'datetime'):
                botocore.auth.datetime = MockDatetime
            
            session = boto3.Session(
                aws_access_key_id=ACCESS_KEY,
                aws_secret_access_key=SECRET_KEY,
                region_name="us-east-1"
            )
            
            sts = session.client('sts')
            
            try:
                print("   Sending GetCallerIdentity request...")
                identity = sts.get_caller_identity()
                print("\n✅ CREDENTIALS VERIFIED!")
                print(f"   Arn: {identity['Arn']}")
                print(f"   Account: {identity['Account']}")
                print(f"   UserId: {identity['UserId']}")
                return True
            except Exception as e:
                print(f"\n❌ Verification Failed: {e}")
                return False

if __name__ == "__main__":
    verify_with_offset()
