# Pdf to excel
```bash
pip install -r requirements.txt
```

```
cp .env.example .env
```

Update .env with your configuration:

```
GEMINI_API_KEY=your_gemini_api_key

R2_ENDPOINT_URL=https://<your-r2-endpoint>
R2_ACCESS_KEY_ID=<your-access-key-id>
R2_SECRET_ACCESS_KEY=<your-secret-access-key>
R2_BUCKET_NAME=<your-bucket-name>
R2_REGION=auto

S3_BASE_URL=https://<your-s3-base-url>
S3_FOLDER=pdftoexcel
```
Then run

```
python app/main.py
```
