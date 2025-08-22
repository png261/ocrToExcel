from pathlib import Path
import os, uuid, requests, base64, asyncio
from dotenv import load_dotenv

import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

import gemini
import excel 
import s3

load_dotenv()


PARSE_URL = os.getenv("PARSE_URL")
OUTPUT_DIR = Path("output"); OUTPUT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="File to Excel API", description="API chuyển đổi file PDF/Images thành file Excel")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
import re
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
        # print("md_content:", md_content)
        # print("result:", result)

        import re

        def split_md_by_paragraphs(md_content, max_lines=300):
            # Tách đoạn theo "\n\n" trở lên
            paragraphs = re.split(r'\n\s*\n', md_content)

            chunks, buf, line_count = [], [], 0
            for para in paragraphs:
                lines = para.splitlines(keepends=True)
                if line_count + len(lines) > max_lines and buf:
                    # Khi đủ ngưỡng thì flush chunk
                    chunks.append("\n\n".join(buf).strip())
                    buf, line_count = [], 0
                buf.append(para)
                line_count += len(lines)

            if buf:
                chunks.append("\n\n".join(buf).strip())

            return chunks

        # parts = re.split(r'(?=^#+\s)', md_content, flags=re.MULTILINE)
        parts = split_md_by_paragraphs(md_content, max_lines=50)
        # Xoá chuỗi rỗng hoặc khoảng trắng dư thừa
        parts = [p.strip() for p in parts if p.strip()]

        print("md_content:", parts)
        print("parts:", len(parts))
        # for i in parts:
        #     data = gemini.markdownToJson(i)
        #     if not data: raise HTTPException(422, "Không thể xử lý nội dung file Markdown")
        #     print("data:", data)
        data = []
        for idx, part in enumerate(parts):
            try:
                print(f"Processing chunk {idx+1}/{len(parts)}...")
                chunk_data = gemini.markdownToJson(part) 
                if isinstance(chunk_data, list):
                    data.extend(chunk_data)  
                else:
                    print(f"Cảnh báo: chunk {idx} không phải list → bỏ qua")
            except Exception as e:
                print(f"Lỗi xử lý chunk {idx}: {e}")

        print("Data full:", data)
        output_filename = f"{name}_{uuid.uuid4().hex[:8]}.xlsx"
        output_path = OUTPUT_DIR / output_filename
        excel.toExcel(data, image_urls_map, output_path)
        if not output_path.exists(): raise HTTPException(500, "Lỗi khi tạo file Excel")

        return FileResponse(output_path, filename=output_filename, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    except Exception as e:
        raise HTTPException(500, f"Lỗi server: {e}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="debug")

