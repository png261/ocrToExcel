from pathlib import Path
import os, uuid, requests, base64, asyncio
from dotenv import load_dotenv

import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import re

import gemini
import excel 
import s3
import save
import md_to_json
import gen_qa

load_dotenv()

PARALLEL_WORKERS = 8
MAX_LINES_PER_CHUNK = 60 

PARSE_URL = os.getenv("PARSE_URL")
OUTPUT_DIR = Path("output"); OUTPUT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="File to Excel API", description="API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class MarkdownRequest(BaseModel):
    markdown_text: str

@app.post("/to_excel")
async def file_to_excel(file: UploadFile = File(...)):
    name = Path(file.filename).stem
    ext = Path(file.filename).suffix.lower()
    if ext not in [".pdf", ".png", ".jpg", ".jpeg"]:
        raise HTTPException(422, "Chỉ hỗ trợ PDF và các định dạng ảnh PNG, JPG, JPEG")

    try:
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
        md_content = re.sub(
            r'!\[\]\(images/', 
            '![ ](https://static-ai.hoclieu.vn/pdftoexcel/', 
            md_content
        )

        def split_by_cau_or_question(md_content: str, max_lines: int = 300):
            lines = md_content.splitlines()  
            chunks = []
            for i in range(0, len(lines), max_lines):
                chunk = "\n".join(lines[i:i + max_lines]).strip()
                if chunk:
                    chunks.append(chunk)
            return chunks
        parts = split_by_cau_or_question(md_content, max_lines=MAX_LINES_PER_CHUNK)
        print("parts:", len(parts), "chunks")
        print("len parts:", len(parts))

        print(f"Starting parallel processing with {PARALLEL_WORKERS} workers...")
        chunk_results = await gemini.process_chunks_parallel(parts, max_workers=PARALLEL_WORKERS)

        data = ""
        for idx, chunk_data in enumerate(chunk_results):
            if chunk_data and chunk_data.strip():
                chunk_lines = chunk_data.count('\n') + 1
                if data:
                    data = data + "\n\n" + chunk_data
                else:
                    data = chunk_data
                print(f"Added chunk {idx+1} ({chunk_lines} lines), total length: {len(data)}")
            else:
                print(f"Skipped empty chunk {idx+1}")
        
        print(f"Parallel processing completed! Total chunks: {len(parts)}")
        with open("output_cleaned.md", "w", encoding="utf-8") as f:
            f.write(data)
        print("Data full length:", len(data))
        print("Data preview:", data[:300] + "..." if len(data) > 300 else data)

        return {"data": data, "total_chunks": len(parts), "data_length": len(data)}

    except Exception as e:
        raise HTTPException(500, f"Lỗi server: {e}")

@app.post("/save")
async def markdown_to_excel(request: MarkdownRequest):
    try:
        markdown_text = request.markdown_text
        
        if not markdown_text.strip():
            raise HTTPException(400, "Markdown text không được để trống")
        
        filename = "output.xlsx"
        output_path = OUTPUT_DIR / filename        
        excel_path = save.markdown_to_excel(markdown_text, str(output_path))
        if not Path(excel_path).exists():
            raise HTTPException(500, "Không thể tạo file Excel")
        
        return FileResponse(
            path=excel_path,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Lỗi khi chuyển đổi markdown sang Excel: {e}")
    
@app.post("/to_json")
async def markdown_to_json_endpoint(request: MarkdownRequest):
    try:
        markdown_text = request.markdown_text
        if not markdown_text.strip():
            raise HTTPException(400, "Markdown text không được để trống")
        json_data = md_to_json.markdown_to_json(markdown_text)
        
        return {
            "success": True,
            "data": json_data,
            "total_questions": len(json_data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Lỗi khi chuyển đổi markdown sang JSON: {e}")

@app.post("/api/v1/book-embedding/generate-question")
def generateQuestionBy9Anh(request: gen_qa.generateQuestionBy9Anh):
    
    content = gen_qa.find_content_by_topic(request.grade, request.subject, request.topic)
    response_data = {
        "name": f"{request.subject} - Grade {request.grade} - {', '.join(request.topic) if request.topic else 'General'}",
        "questions": []
    }
    
    questions = gen_qa.genqa(
        amount=request.amount,
        grade=request.grade,
        note=request.note,
        questionType=request.questionType,
        subject=request.subject,
        topic=request.topic,
        content=content
    )
    
    response_data["questions"] = questions
    
    return response_data

@app.post("/api/v1/marker/generate-question")
def generateQuestionBy9AnhWithTopic(request: gen_qa.generateQuestionBy9AnhWithTopic1):

    print(f"Received request: {request}")
    response_data = {
        "name": f"{request.subject} - Grade {request.grade}",
        "questions": []
    }
    
    print(f"Request details: amount={request.amount}, grade={request.grade}, document={request.document},questionType={request.questionType}, subject={request.subject}")
    # print(f"Note: {request.note if request.note else 'No note provided'}")
    questions = gen_qa.genqa_with_doc(
        amount=request.amount,
        grade=request.grade,
        questionType=request.questionType,
        subject=request.subject,
        document = request.document
    )
    
    response_data["questions"] = questions
    
    return response_data

@app.post("/api/v1/marker/generate-derivative-question-advanced")
def generateDerivativeQuestion(request: gen_qa.GenerateDerivativeQuestionRequest):
    
    print(f"Received derivative question request: {request}")
    response_data = {
        "name": f"{request.subject} - Grade {request.grade}",
        "questions": []
    }
    
    print(f"Request details: amount={request.amount}, grade={request.grade}, note={request.note}, originalQuestion={request.originalQuestion[:100]}..., questionType={request.questionType}, subject={request.subject}")
    
    questions = gen_qa.genqa_derivative(
        amount=request.amount,
        grade=request.grade,
        note=request.note,
        originalQuestion=request.originalQuestion,
        questionType=request.questionType,
        subject=request.subject
    )
    
    response_data["questions"] = questions
    
    return response_data


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="debug")

