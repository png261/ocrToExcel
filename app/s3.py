import boto3
import os, uuid, requests, base64, asyncio
from concurrent.futures import ThreadPoolExecutor

R2 = {
    "endpoint_url": os.getenv("R2_ENDPOINT_URL"),
    "access_key": os.getenv("R2_ACCESS_KEY_ID"),
    "secret_key": os.getenv("R2_SECRET_ACCESS_KEY"),
    "bucket": os.getenv("R2_BUCKET_NAME"),
    "region": os.getenv("R2_REGION", "auto")
}
S3_BASE_URL = os.getenv("S3_BASE_URL")
S3_FOLDER = os.getenv("S3_FOLDER", "pdftoexcel")

# ---- R2 client ----
r2_client = boto3.client(
    "s3",
    endpoint_url=R2["endpoint_url"],
    aws_access_key_id=R2["access_key"],
    aws_secret_access_key=R2["secret_key"],
    region_name=R2["region"]
)

executor = ThreadPoolExecutor(max_workers=8)

def upload_to_r2(file_bytes: bytes, filename: str, folder: str):
    """Upload file to R2/S3."""
    r2_client.put_object(Bucket=R2["bucket"], Key=f"{folder}/{filename}", Body=file_bytes)

async def upload_images(images: dict) -> dict:
    """Upload multiple images concurrently and return mapping to URLs."""
    loop = asyncio.get_event_loop()
    tasks = []
    url_map = {}
    for img_name, img_b64 in images.items():
        img_bytes = base64.b64decode(img_b64.split(",", 1)[-1])
        url_map[f"images/{img_name}"] = f"{S3_BASE_URL}/{S3_FOLDER}/{img_name}"
        tasks.append(loop.run_in_executor(executor, upload_to_r2, img_bytes, img_name, S3_FOLDER))
    await asyncio.gather(*tasks)
    return url_map

