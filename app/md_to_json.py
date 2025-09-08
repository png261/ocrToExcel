import json as json_module
import sys
import os
import re
from typing import List, Dict, Any

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from save import split_questions, classify_and_build, convert_to_excel_format

def parse_text_format(text: str) -> Dict[str, Any]:
    has_bold = bool(re.search(r'<b>.*?</b>', text))
    has_italic = bool(re.search(r'<i>.*?</i>', text))
    has_underline = bool(re.search(r'<u>.*?</u>', text))
    
    # Nếu không có thẻ format nào thì return Paragraph
    if not (has_bold or has_italic or has_underline):
        return {
            "type": "Paragraph", 
            "content": text.strip()
        }
    
    # Có thẻ format thì return TextRunHTML (giữ nguyên HTML tags)
    return {
        "type": "TextRunHTML",
        "content": text.strip()
    }

def convert_to_new_format(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    new_format_data = []
    
    for item in items:
        item_type = item["type"]
        data = item["data"]
        images = item.get("images", [])
        
        if item_type == "MultipleChoiceQuestion":
            question_obj = parse_text_format(data["prompt"])
            choices = {}
            for i, opt in enumerate(data["options"], 1):
                if i <= 10: 
                    choice_obj = parse_text_format(opt["text"])
                    choice_obj["isCorrect"] = (opt["label"] == data.get("answer"))
                    choices[f"choice{i}"] = choice_obj
            
            new_item = {
                "questionType": "Multiple Choice",
                "difficulty_Level": "Nhận biết (Remembering)",
                "children": {
                    "Question": question_obj,
                    **choices
                }
            }
            
            if images:
                new_item["children"]["image"] = images[0]  
            
            new_format_data.append(new_item)
            
        elif item_type == "CheckboxQuestion":
            question_obj = parse_text_format(data["prompt"])
            choices = {}
            correct_answers = data.get("answers", [])
            
            for i, opt in enumerate(data["options"], 1):
                if i <= 10:
                    choice_obj = parse_text_format(opt["text"])
                    choice_obj["isCorrect"] = (opt["label"] in correct_answers)
                    choices[f"choice{i}"] = choice_obj
            
            new_item = {
                "questionType": "Checkbox",
                "difficulty_Level": "Nhận biết (Remembering)",
                "children": {
                    "Question": question_obj,
                    **choices
                }
            }
            
            if images:
                new_item["children"]["image"] = images[0]
                
            new_format_data.append(new_item)
            
        elif item_type == "TrueFalseQuestion":
            question_obj = parse_text_format(data["prompt"])
            
            statements = {}
            for i, statement_data in enumerate(data["items"], 1):
                statement_obj = parse_text_format(statement_data["statement"])
                statement_obj["isCorrect"] = statement_data["answer"]
                statements[f"statement{i}"] = statement_obj
            
            new_item = {
                "questionType": "True False",
                "difficulty_Level": "Nhận biết (Remembering)",
                "children": {
                    "Question": question_obj,
                    **statements
                }
            }
            
            if images:
                new_item["children"]["image"] = images[0]
                
            new_format_data.append(new_item)
            
        elif item_type == "FillInQuestion":
            question_obj = parse_text_format(data["prompt"])
            formatted_answers = []
            for answer in data.get("answers", []):
                answer_obj = parse_text_format(answer)
                formatted_answers.append(answer_obj)
            
            new_item = {
                "questionType": "Fill In",
                "difficulty_Level": "Nhận biết (Remembering)",
                "children": {
                    "Question": question_obj,
                    "answers": formatted_answers
                }
            }
            
            if images:
                new_item["children"]["image"] = images[0]
                
            new_format_data.append(new_item)
            
        elif item_type == "MatchingOneQuestion":
            question_obj = parse_text_format("Nối các cặp sau:")
            
            pairs = {}
            for i, pair in enumerate(data["pairs"], 1):
                if i <= 10:  
                    left_obj = parse_text_format(pair["left"])
                    right_obj = parse_text_format(pair["right"])
                    pairs[f"pair{i}"] = {
                        "left": left_obj,
                        "right": right_obj
                    }
            
            new_item = {
                "questionType": "Matching",
                "difficulty_Level": "Nhận biết (Remembering)",
                "children": {
                    "Question": question_obj,
                    **pairs
                }
            }
            
            if images:
                new_item["children"]["image"] = images[0]
                
            new_format_data.append(new_item)
            
        elif item_type == "EssayQuestion":
            question_obj = parse_text_format(data["prompt"])
            
            if "ordering" in data.get("params", {}):
                ordering_data = data["params"]["ordering"]
                items = {}
                for i, item_data in enumerate(ordering_data["items"], 1):
                    if i <= 10:  
                        item_obj = parse_text_format(item_data["text"])
                        items[f"item{i}"] = item_obj
                
                new_item = {
                    "questionType": "Order Items",
                    "difficulty_Level": "Nhận biết (Remembering)",
                    "children": {
                        "Question": question_obj,
                        **items,
                        "correctOrder": ordering_data["correct_sequence"]
                    }
                }
            else:
                new_item = {
                    "questionType": "Essay",
                    "difficulty_Level": "Nhận biết (Remembering)",
                    "children": {
                        "Question": question_obj
                    }
                }
            
            if images:
                new_item["children"]["image"] = images[0]
                
            new_format_data.append(new_item)
    
    return new_format_data

def markdown_to_json(md: str, use_new_format: bool = True) -> List[Dict[str, Any]]:
    blocks = split_questions(md)
    parsed_items = []
    for b in blocks:
        item = classify_and_build(b["index"], b["text"], b.get("images", []))
        parsed_items.append(item)
    
    if use_new_format:
        return convert_to_new_format(parsed_items)
    else:
        return convert_to_excel_format(parsed_items)

def save_json_to_file(json_data: List[Dict[str, Any]], output_path: str = None) -> str:
    if output_path is None:
        import time
        timestamp = int(time.time())
        output_path = f"output/converted_questions_new_format_{timestamp}.json"  
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json_module.dump(json_data, f, ensure_ascii=False, indent=2)
    
    print(f"Đã tạo file JSON với format mới: {output_path}")
    print(f"Tổng số câu hỏi: {len(json_data)}")
    
    return output_path

markdown_content = r"""
Câu 1. Trong các đa thức sau, đa thức nào là đa thức một biến?
![](https://static-ai.hoclieu.vn/pdftoexcel/8c3bc09223d3cc6e0556cf6ee0ea212a6e73d135a76e36b8789dd70e808e5756.jpg)
A. $7xy-1$
*B. $x^3 + 4x^2 - 3$
C. $8x^2y - x$
D. $2xy-y$
Giải thích: adjnjjfsa
Câu 2. <b>Trong các đa thức sau, đa thức nào là đa thức một biến?</b>
A. $7xy-1$
*B. $x^3 + 4x^2 - 3$
*C. $8x^2y - x$
D. $2xy-y$

Câu 3. <i>Bạn Hà mở ngẫu nhiên một cuốn sách có 188 trang. Xét biến cố: Trang sách bạn Hà mở được là một số chia hết cho 3. Tính xác suất của biến cố đó</i>.

Câu 4.<u> Cho tam giác ABC cân tại A. Hai đường phân giác BM và CE cắt nhau tại I. </u>Trong các khẳng định sau. Khẳng định nào đúng, khẳng định nào sai ?
*Sai Điểm I cách đều ba đỉnh của tam giác ABC.)
*Đúng (Tam giác IBC cân tại I)
*Đúng $\widehat{IAB} + \widehat{IBC} + \widehat{ICA} = 90^{\circ}$)
*Sai Nếu $\widehat{BAC} = 40^{\circ}$ thì $\widehat{BIC} = 130^{\circ}$)

Câu 5. Trong tiết học Khoa học, cô giáo mang đến một chiếc __chiếc bóng đèn__ để minh họa cho bài về năng lượng. Khi chiếu ánh sáng mặt trời qua __abcc__, chúng ta có thể nhìn thấy nhiều __màu sắc__ khác nhau.

Câu 6. Sắp xếp
(3)<i>Ghi lại sự thay đổi của cây hằng ngày</i>
(2)Tưới nước vừa đủ mỗi ngày
(4)Cho hạt đậu vào cốc nhựa có bông gòn ẩm
(1)Đặt cốc ở nơi có ánh sáng

Câu 7. <i>Nối</i>
Trái Đất -> Hành tinh duy nhất có sự sống
Sao Hỏa -> Hành tinh đỏ, có núi lửa lớn
Sao Mộc -> Hành tinh lớn nhất, có Vết Đỏ Lớn
""".strip()

if __name__ == "__main__":
    result = markdown_to_json(markdown_content)
    print(json_module.dumps(result, ensure_ascii=False, indent=2))
    
    output_file = save_json_to_file(result)
    print(f"\nFile JSON đã được lưu tại: {output_file}")