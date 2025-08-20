from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import os, uuid, requests, base64, asyncio
from dotenv import load_dotenv
import gemini
from excel_process import convert_history_json_to_excel_strict
import s3
import uvicorn

# ---- Load config ----
load_dotenv()


PARSE_URL = os.getenv("PARSE_URL")
OUTPUT_DIR = Path("output"); OUTPUT_DIR.mkdir(exist_ok=True)

# ---- FastAPI app ----
app = FastAPI(title="File to Excel API", description="API chuyển đổi file PDF/Images thành file Excel")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ---- Endpoint ----
@app.post("/to_excel")
async def file_to_excel(file: UploadFile = File(...)):
    name = Path(file.filename).stem
    ext = Path(file.filename).suffix.lower()
    if ext not in [".pdf", ".png", ".jpg", ".jpeg"]:
        raise HTTPException(422, "Chỉ hỗ trợ PDF và các định dạng ảnh PNG, JPG, JPEG")

    try:
        # 1️⃣ Send file to parse service
        res = requests.post(
            PARSE_URL,
            files={"files": (file.filename, file.file, file.content_type)},
            data={
                "lang_list":"en","backend":"pipeline","parse_method":"auto",
                "formula_enable":"true","table_enable":"true","server_url":"",
                "return_md":"true","return_images":"true","start_page_id":"0","end_page_id":"99999"
            }
        )
        res.raise_for_status()
        result = res.json().get("results", {}).get(name)
        if not result: raise HTTPException(422, "Không có kết quả trả về từ dịch vụ parse file")

        md_content, images = result.get("md_content"), result.get("images", {})
        image_urls_map = await s3.upload_images(images)

        # 2️⃣ Markdown -> Excel
        data = gemini.markdownToJson(md_content)
        if not data: raise HTTPException(422, "Không thể xử lý nội dung file Markdown")

        output_filename = f"{name}_{uuid.uuid4().hex[:8]}.xlsx"
        output_path = OUTPUT_DIR / output_filename
        convert_history_json_to_excel_strict(data, image_urls_map, output_path)
        if not output_path.exists(): raise HTTPException(500, "Lỗi khi tạo file Excel")

        return FileResponse(output_path, filename=output_filename, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    except Exception as e:
        raise HTTPException(500, f"Lỗi server: {e}")

# ---- Run server ----
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="debug")

