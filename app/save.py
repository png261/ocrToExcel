
import re
import json
import sys
import os
from typing import List, Dict, Any, Optional

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

markdown_content = r"""
Câu 1. Trong các đa thức sau, đa thức nào là đa thức một biến?
![](https://static-ai.hoclieu.vn/pdftoexcel/8c3bc09223d3cc6e0556cf6ee0ea212a6e73d135a76e36b8789dd70e808e5756.jpg)
A. $7xy-1$
*B. $x^3 + 4x^2 - 3$
C. $8x^2y - x$
D. $2xy-y$

Câu 2. Trong các đa thức sau, đa thức nào là đa thức một biến?
A. $7xy-1$
*B. $x^3 + 4x^2 - 3$
*C. $8x^2y - x$
D. $2xy-y$

Câu 3. Bạn Hà mở ngẫu nhiên một cuốn sách có 188 trang. Xét biến cố: Trang sách bạn Hà mở được là một số chia hết cho 3. Tính xác suất của biến cố đó.

Câu 4. Cho tam giác ABC cân tại A. Hai đường phân giác BM và CE cắt nhau tại I. Trong các khẳng định sau. Khẳng định nào đúng, khẳng định nào sai ?
*Sai Điểm I cách đều ba đỉnh của tam giác ABC.)
*Đúng (Tam giác IBC cân tại I)
*Đúng $\widehat{IAB} + \widehat{IBC} + \widehat{ICA} = 90^{\circ}$)
*Sai Nếu $\widehat{BAC} = 40^{\circ}$ thì $\widehat{BIC} = 130^{\circ}$)

Câu 5. Trong tiết học Khoa học, cô giáo mang đến một chiếc __chiếc bóng đèn__ để minh họa cho bài về năng lượng. Khi chiếu ánh sáng mặt trời qua ____, chúng ta có thể nhìn thấy nhiều __màu sắc__ khác nhau.

Câu 6. Sắp xếp
(3)Ghi lại sự thay đổi của cây hằng ngày
(2)Tưới nước vừa đủ mỗi ngày
(4)Cho hạt đậu vào cốc nhựa có bông gòn ẩm
(1)Đặt cốc ở nơi có ánh sáng

Câu 7. Nối
Trái Đất --> Hành tinh duy nhất có sự sống
Sao Hỏa --> Hành tinh đỏ, có núi lửa lớn
Sao Mộc --> Hành tinh lớn nhất, có Vết Đỏ Lớn
""".strip()

def extract_images_from_text(text: str) -> tuple[str, list[str]]:
    image_pattern = r'!\[.*?\]\((https://[^)]+)\)' 
    image_urls = re.findall(image_pattern, text) 
    clean_text = re.sub(image_pattern, '', text)
    clean_text = re.sub(r'\n\s*\n', '\n', clean_text).strip()
    
    return clean_text, image_urls

def split_questions(md: str) -> List[Dict[str, Any]]:
    parts = re.split(r'\n(?=Câu\s+\d+\.)', '\n' + md.strip())
    blocks = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        m = re.match(r'^Câu\s+(\d+)\.\s*(.*)', p, flags=re.IGNORECASE | re.DOTALL)
        if not m:
            continue
        idx = int(m.group(1))
        rest = m.group(2).strip()
        
        clean_text, image_urls = extract_images_from_text(rest)
        
        blocks.append({
            "index": idx, 
            "text": clean_text,
            "images": image_urls  
        })
    return blocks

_choice_rx = re.compile(r'^\*?[A-D]\.\s*(.+)$')
_choice_marked_rx = re.compile(r'^\*(?P<label>[A-D])\.\s*(?P<text>.+)$')
_choice_any_rx = re.compile(r'^(?P<label>[A-D])\.\s*(?P<text>.+)$')

def parse_choices(lines: List[str]):
    choices = []
    correct_labels = set()
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        m_star = _choice_marked_rx.match(ln)
        m_norm = _choice_any_rx.match(ln)
        if m_star:
            label, text = m_star.group('label'), m_star.group('text').strip()
            correct_labels.add(label)
            choices.append((label, text))
        elif m_norm:
            label, text = m_norm.group('label'), m_norm.group('text').strip()
            choices.append((label, text))
    return choices, sorted(list(correct_labels))

def looks_like_choice_block(text: str) -> bool:
    return bool(re.search(r'^[\*]?[A-D]\.\s', text, flags=re.MULTILINE))

def extract_prompt_and_option_block(text: str):
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return "", []
    prompt_lines = []
    option_lines = []
    reached_options = False
    for ln in lines:
        if re.match(r'^\*?[A-D]\.\s', ln):
            reached_options = True
            option_lines.append(ln)
        else:
            if reached_options:
                option_lines.append(ln)  
            else:
                prompt_lines.append(ln)
    return " ".join(prompt_lines).strip(), option_lines

def is_true_false_block(text: str) -> bool:
    return bool(re.search(r'^\*(Đúng|Sai)\b', text, flags=re.MULTILINE | re.IGNORECASE))

def parse_true_false(text: str):
    items = []
    for ln in text.splitlines():
        ln = ln.strip()
        m = re.match(r'^\*(Đúng|Sai)\s*\)?\s*(.*)$', ln, flags=re.IGNORECASE)
        if m:
            val = m.group(1).lower()
            stmt = m.group(2).strip().strip('()').strip()
            items.append({
                "statement": stmt,
                "answer": True if val == "đúng" else False
            })
    return items

def is_fill_in(text: str) -> bool:
    return "__" in text

def parse_fill_in(text: str):
    answers = re.findall(r'__([^_]+?)__', text)
    prompt_original = text.strip()
    blanks = text.count("__") // 2  
    return {
        "prompt": prompt_original, 
        "blanks": blanks,
        "answers": [a.strip() for a in answers] 
    }

def is_matching(text: str) -> bool:
    return "->" in text

def parse_matching(text: str):
    pairs = []
    for ln in text.splitlines():
        if "->" in ln:
            left, right = ln.split("->", 1)
            pairs.append({"left": left.strip(), "right": right.strip()})
    return pairs

def is_ordering(text: str) -> bool:
    if not re.search(r'\bSắp\s*xếp\b', text, flags=re.IGNORECASE):
        return False
    return bool(re.search(r'^\(\d+\)\s*.+$', text, flags=re.MULTILINE))

def parse_ordering(text: str):
    items = []
    answer_order = []  
    for ln in text.splitlines():
        m = re.match(r'^\((\d+)\)\s*(.+)$', ln.strip())
        if m:
            lab = int(m.group(1))
            content = m.group(2).strip()
            items.append({"label": lab, "text": content})
            answer_order.append(lab)  # Thứ tự xuất hiện
    
    correct_sequence = []
    max_label = max(answer_order) if answer_order else 0
    for i in range(1, max_label + 1):
        if i in answer_order:
            position = answer_order.index(i) + 1
            correct_sequence.append(position)
    
    return {
        "instruction": "Sắp xếp các bước theo thứ tự đúng",
        "items": items,
        "answer_order": answer_order,  
        "correct_sequence": correct_sequence 
    }

def classify_and_build(idx: int, raw: str, images: List[str] = None) -> Dict[str, Any]:
    text = raw.strip()
    if images is None:
        images = []

    # 1) Fill-in
    if is_fill_in(text):
        fi = parse_fill_in(text)
        return {
            "index": idx,
            "type": "FillInQuestion",
            "data": {
                "prompt": fi["prompt"],
                "blanks": fi["blanks"],
                "answers": fi["answers"]
            },
            "images": images
        }

    # 2) Matching
    if is_matching(text):
        pairs = parse_matching(text)
        return {
            "index": idx,
            "type": "MatchingOneQuestion",
            "data": {
                "pairs": pairs
            },
            "images": images
        }

    # 3) True/False
    if is_true_false_block(text):
        items = parse_true_false(text)
        prompt = text.splitlines()[0]
        return {
            "index": idx,
            "type": "TrueFalseQuestion",
            "data": {
                "prompt": prompt.strip(),
                "items": items 
            },
            "images": images
        }

    # 4) Ordering (map vào Essay + param)
    if is_ordering(text):
        od = parse_ordering(text)
        return {
            "index": idx,
            "type": "EssayQuestion",
            "data": {
                "prompt": "Sắp xếp các bước",
                "params": {"ordering": od}  
            },
            "images": images
        }

    # 5) Choice (MCQ/Checkbox)
    if looks_like_choice_block(text):
        prompt, option_lines = extract_prompt_and_option_block(text)
        choices, correct_labels = parse_choices(option_lines)
        options = [{"label": lb, "text": tx} for lb, tx in choices]
        if len(correct_labels) <= 1:
            return {
                "index": idx,
                "type": "MultipleChoiceQuestion",
                "data": {
                    "prompt": prompt,
                    "options": options,
                    "answer": correct_labels[0] if correct_labels else None
                },
                "images": images
            }
        else:
            return {
                "index": idx,
                "type": "CheckboxQuestion",
                "data": {
                    "prompt": prompt,
                    "options": options,
                    "answers": correct_labels
                },
                "images": images
            }

    # 6) Mặc định Essay
    return {
        "index": idx,
        "type": "EssayQuestion",
        "data": {
            "prompt": text,
            "params": {}
        },
        "images": images
    }

def convert_to_excel_format(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    excel_data = []
    
    for item in items:
        excel_item = {
            "Question": "",
            "Question type": "",
            "Difficulty level": "Nhận biết (Remembering)",
            "image": ""
        }
        
        item_type = item["type"]
        data = item["data"]
        images = item.get("images", [])
    
        if images:
            excel_item["image"] = "; ".join(images)
        
        if item_type == "MultipleChoiceQuestion":
            excel_item["Question"] = data["prompt"]
            excel_item["Question type"] = "Multiple Choice"
            excel_item["options"] = [opt["text"] for opt in data["options"]]
            
            # Tìm vị trí đáp án đúng
            if data.get("answer"):
                for i, opt in enumerate(data["options"]):
                    if opt["label"] == data["answer"]:
                        excel_item["answer"] = i + 1
                        break
            else:
                excel_item["answer"] = 1
                
        elif item_type == "CheckboxQuestion":
            excel_item["Question"] = data["prompt"]
            excel_item["Question type"] = "Checkbox"
            excel_item["options"] = [opt["text"] for opt in data["options"]]
            
            # Tìm vị trí các đáp án đúng
            correct_indices = []
            for answer_label in data.get("answers", []):
                for i, opt in enumerate(data["options"]):
                    if opt["label"] == answer_label:
                        correct_indices.append(i + 1)
                        break
            excel_item["answer"] = correct_indices if correct_indices else [1]
            
        elif item_type == "TrueFalseQuestion":
            excel_item["Question"] = data["prompt"]
            excel_item["Question type"] = "True False"
            statements = []
            for item_data in data["items"]:
                statements.append({
                    "text": item_data["statement"],
                    "answer": item_data["answer"]
                })
            excel_item["statements"] = statements
            
        elif item_type == "FillInQuestion":
            excel_item["Question"] = data["prompt"]  # Giữ nguyên với __đáp_án__
            excel_item["Question type"] = "Fill In"
            excel_item["explanation"] = " | ".join(data.get("answers", []))
            
        elif item_type == "MatchingOneQuestion":
            excel_item["Question"] = "Nối các cặp sau:"
            excel_item["Question type"] = "Matching 1 answer"
            left_items = []
            right_items = []
            
            for i, pair in enumerate(data["pairs"]):
                left_items.append(pair["left"])
                right_items.append(pair["right"])
                
            excel_item["left"] = left_items
            excel_item["right"] = right_items
            
        elif item_type == "EssayQuestion":
            excel_item["Question"] = data["prompt"]
            if "ordering" in data.get("params", {}):
                excel_item["Question type"] = "Order items"
                ordering_data = data["params"]["ordering"]
                
                # Giữ nguyên thứ tự xuất hiện trong markdown (không sắp xếp)
                items = [item_data["text"] for item_data in ordering_data["items"]]
                excel_item["items"] = items
                
                # Đáp án là thứ tự đúng (4-2-1-3 cho ví dụ (3)(2)(4)(1))
                answer_sequence = "-".join(map(str, ordering_data["correct_sequence"]))
                excel_item["answer"] = answer_sequence
                
            else:
                excel_item["Question type"] = "Essay"
                excel_item["explanation"] = ""
        
        excel_data.append(excel_item)
    
    return excel_data

def markdown_to_excel(markdown_content: str, output_excel_path: str = None) -> str:
    from excel import toExcel
    
    # Parse markdown
    blocks = split_questions(markdown_content)
    parsed_items = []
    
    for b in blocks:
        item = classify_and_build(b["index"], b["text"], b.get("images", []))
        parsed_items.append(item)
    
    excel_data = convert_to_excel_format(parsed_items)
    if output_excel_path is None:
        output_excel_path = "output/converted_questions.xlsx"
    os.makedirs(os.path.dirname(output_excel_path), exist_ok=True)
    toExcel(excel_data, output_path=output_excel_path)
    
    print(f"Đã tạo file Excel: {output_excel_path}")
    print(f"Tổng số câu hỏi: {len(excel_data)}")
    
    return output_excel_path

def markdown_to_excel_simple(markdown_content: str, output_excel_path: str = None) -> str:

    return markdown_to_excel(markdown_content, output_excel_path)

def main(md: str, output_excel_path: str = None):
    from excel import toExcel
    
    blocks = split_questions(md)
    out_all = []
    
    for b in blocks:
        item = classify_and_build(b["index"], b["text"], b.get("images", []))
        out_all.append(item)

    excel_data = convert_to_excel_format(out_all)
    
    if output_excel_path is None:
        import time
        timestamp = int(time.time())
        output_excel_path = f"output/converted_questions_{timestamp}.xlsx"
    
    toExcel(excel_data, output_path=output_excel_path)
    print(f"Đã tạo file Excel: {output_excel_path}")
    print(f"Tổng số câu hỏi: {len(excel_data)}")
    
    return excel_data

if __name__ == "__main__":
    import os
    os.makedirs("output", exist_ok=True)

    main(markdown_content)
