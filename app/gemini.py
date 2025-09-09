import google.generativeai as genai
import json
import re
import os
import asyncio
import concurrent.futures
from dotenv import load_dotenv

load_dotenv()

def get_prompt(content):
    return """
Bạn là AI phân tích tài liệu để kiểm tra chính tả và trả về dữ liệu theo cấu trúc markdown.

Đầu vào: Nội dung của tài liệu: """ + content + """

Đầu ra: **CHỈ TRẢ VỀ NỘI DUNG MARKDOWN** theo cấu trúc bên dưới, KHÔNG thêm tiêu đề hay giải thích gì khác.

## Ví dụ cấu trúc markdown:
Câu 1. Thủ đô của Việt Nam là?
![](images/c6a94a04c14f43ff7c6c769f73e08e4280e65835b4e8ea88d7826ece69288f00.jpg)
A. Hà Nội
*B. TP.HCM
C. Đà Nẵng
D. Cần Thơ

Câu 2. Phân tích vai trò của giáo dục

Câu 3. Điền vào chỗ trống:
Trong tiết học Khoa học, cô giáo mang đến một chiếc __chiếc bóng đèn__ để minh họa cho bài về năng lượng. Chúng ta có thể nhìn thấy nhiều __màu sắc__ khác nhau.

Câu 4: (2,0 điểm) Cho tam giác ABC cân tại A. Kẻ BE vuông góc với AC tại E và CF vuông góc với AB tại F.
a) Chứng minh: $AE = AF$
b) Gọi D là giao điểm của BE và CF, AD cắt BC tại H. Chứng minh AH là tia phân giác của góc BAC.

Câu 5. Đánh giá tính đúng sai:
*Đúng Việt Nam có 63 tỉnh thành
*Sai Thủ đô là TP.HCM
*Sai Việt Nam ở Châu Âu

Câu 6. Nối tên thành phố với vùng miền:
Hà Nội -> Miền Bắc
TP.HCM -> Miền Nam
Đà Nẵng -> Miền Trung

Câu 7. Nối tên thành phố với vùng miền:( nối 1 đáp án với nhiều đáp án)
Hà Nội -> Miền Bắc:: Thủ đô
TP.HCM -> Miền Nam:: Trung tâm kinh tế
Đà Nẵng -> Miền Trung :: Thành phố biển

Câu 8. Sắp xếp
(3)Ghi lại sự thay đổi của cây hằng ngày
(2)Tưới nước vừa đủ mỗi ngày
(4)Cho hạt đậu vào cốc nhựa có bông gòn ẩm
(1)Đặt cốc ở nơi có ánh sáng

## Quy tắc:
1. **CHỈ TRẢ VỀ NỘI DUNG CÂU HỎI** - không thêm tiêu đề, giải thích
2. **Công thức toán/lý/hóa**: Dùng LaTeX với `$...$` (inline) hoặc `$$...$$` (display)
3. **Format câu hỏi**: Câu 1., Câu 2., ...
4. **Đáp án đúng**: Thêm dấu * phía trước
5. **Lựa chọn của trắc nghiệm một hoặc nhiều đáp án**: A., B., C., D. 
6. **Dạng đúng sai có dạng: *Đúng (Nội dung đáp án) hoặc *Sai (Nội dung đáp án) hoặc **Không xác định (Nội dung đáp án)**
7. **Ảnh**: ![](url)
8. **Không bỏ sót câu nào**
9. **Sửa lỗi chính tả** nhưng giữ nguyên nội dung
10. **Quan trọng nhất** Chỉ lấy nhưng câu là câu hỏi thôi nếu không phải câu hỏi thì bỏ qua
11. **Nếu câu hỏi tự luận có nhiều ý thì ý con sẽ bắt đầu bằng a);b)...**
12. **Nếu dạng nối nhiều đáp án thì dùng :: để phân cách**
13. ** Lưu ý không cho katex vào nháy ``.
"""


def markdownToMarkdown(content):
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    
    # Cấu hình safety settings để giảm việc bị block
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    
    model = genai.GenerativeModel('gemini-2.5-flash')
    prompt = get_prompt(content)
    
    try:
        response = model.generate_content(prompt, safety_settings=safety_settings)
        
        # Kiểm tra response có hợp lệ không
        if not response or not response.candidates:
            print("No candidates in response")
            print(f"Response: {response}")
            return ""
            
        candidate = response.candidates[0]
        if not hasattr(candidate, 'content') or not candidate.content:
            print("No content in candidate")
            print(f"Candidate: {candidate}")
            return ""
            
        if not hasattr(candidate.content, 'parts') or not candidate.content.parts:
            print("No parts in content")
            print(f"Content: {candidate.content}")
            # Kiểm tra xem có bị block bởi safety filters không
            if hasattr(candidate, 'finish_reason'):
                print(f"Finish reason: {candidate.finish_reason}")
            if hasattr(candidate, 'safety_ratings'):
                print(f"Safety ratings: {candidate.safety_ratings}")
            return ""
            
        part = candidate.content.parts[0]
        if hasattr(part, 'text') and isinstance(part.text, str):
            result_text = part.text
            return result_text
        else:
            print("No text in part")
            print(f"Part: {part}")
            return ""
            
    except Exception as e:
        print('Gemini API error:', e)
        print(f'Response object: {response if "response" in locals() else "No response"}')
        return ""

def process_single_chunk(chunk_data):
    """Xử lý một chunk đơn lẻ với retry mechanism"""
    index, content = chunk_data
    max_retries = 2
    
    for attempt in range(max_retries + 1):
        try:
            part_lines = content.count('\n') + 1 if content else 0
            if attempt == 0:
                print(f"Processing chunk {index+1} ({part_lines} lines) in parallel...")
            else:
                print(f"Retry {attempt} for chunk {index+1}...")
            
            result = markdownToMarkdown(content)
            
            if result and result.strip():
                result_lines = result.count('\n') + 1
                print(f"Completed chunk {index+1} ({result_lines} output lines)")
                return (index, result)
            else:
                if attempt < max_retries:
                    print(f"Chunk {index+1} returned empty, retrying...")
                    continue
                else:
                    print(f"Chunk {index+1} failed after {max_retries} retries")
                    return (index, "")
                    
        except Exception as e:
            if attempt < max_retries:
                print(f"Error processing chunk {index+1} (attempt {attempt+1}): {e}, retrying...")
                continue
            else:
                print(f"Error processing chunk {index+1} after {max_retries} retries: {e}")
                return (index, "")
    
    return (index, "")

async def process_chunks_parallel(chunks, max_workers=3):
    """Xử lý tất cả chunks song song và trả về kết quả theo đúng thứ tự"""
    print(f"Starting parallel processing of {len(chunks)} chunks with {max_workers} workers...")
    
    # Tạo dữ liệu với index
    indexed_chunks = [(i, chunk) for i, chunk in enumerate(chunks)]
    
    # Sử dụng ThreadPoolExecutor để chạy song song
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit tất cả tasks
        future_to_index = {
            executor.submit(process_single_chunk, chunk_data): chunk_data[0] 
            for chunk_data in indexed_chunks
        }
        
        # Collect results
        results = {}
        for future in concurrent.futures.as_completed(future_to_index):
            index, result = future.result()
            results[index] = result
    
    # Sắp xếp kết quả theo đúng thứ tự
    ordered_results = []
    for i in range(len(chunks)):
        if i in results:
            ordered_results.append(results[i])
        else:
            ordered_results.append("")
    
    print(f"Completed parallel processing! Total results: {len(ordered_results)}")
    return ordered_results
