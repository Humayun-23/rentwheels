import os
import sys
import boto3
from botocore.config import Config
from dotenv import load_dotenv

def setup_r2_bucket():
    load_dotenv()
    
    account_id = os.getenv("R2_ACCOUNT_ID")
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
    bucket_name = os.getenv("R2_BUCKET_NAME")
    
    if not all([account_id, access_key, secret_key, bucket_name]):
        print("Error: Missing R2 environment variables in .env")
        sys.exit(1)
        
    print(f"Configuring Cloudflare R2 Bucket: {bucket_name}")
    
    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )
    
    # 1. Set CORS Policy (allows frontend to display or interact with items if needed)
    print("Setting CORS configuration...")
    cors_configuration = {
        'CORSRules': [{
            'AllowedHeaders': ['*'],
            'AllowedMethods': ['GET', 'HEAD'],
            'AllowedOrigins': ['*'],
            'ExposeHeaders': [],
            'MaxAgeSeconds': 3000
        }]
    }
    
    try:
        s3.put_bucket_cors(Bucket=bucket_name, CORSConfiguration=cors_configuration)
        print("✅ CORS configured successfully.")
    except Exception as e:
        print(f"❌ Failed to set CORS: {e}")

    # Note: Setting public access via bucket policy in R2 via API can sometimes require
    # the bucket to be configured for public access in the Cloudflare dashboard first.
    # The recommended way for Cloudflare R2 is to go to the dashboard -> R2 -> Bucket -> Settings -> Public Access.
    print("\n--- IMPORTANT ---")
    print("To allow public access to the files without presigned URLs, you must:")
    print("1. Go to your Cloudflare Dashboard.")
    print("2. Navigate to R2 -> Select your bucket -> Settings.")
    print("3. Under 'Public Access', enable 'R2.dev subdomain' OR connect a Custom Domain.")
    print("-----------------\n")

if __name__ == "__main__":
    setup_r2_bucket()
