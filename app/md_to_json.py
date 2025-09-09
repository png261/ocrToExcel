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
A. $7xy-1$
B. $x^3 + 4x^2 - 3$
C. $8x^2y - x$
D. $2xy-y$

Câu 2. Cho đa thức $B(x) = 5x - 20$. Nghiệm của đa thức $B(x)$ là:
A. 4
B. -4
C. 5
D. -5

Câu 3. Đa thức nào đã được sắp xếp theo số mũ giảm dần của biến?
A. $2x^2 - 3x + 1$
B. $1 + x + 3x^2$
C. $2x^7 + 1 + 2x^2$
D. $1 + 2x^2 + 3x^3 + 3x^4 + 3x^4 + 3x^5 + 3x^5 + 3x^4$

Câu 4. Cho đa thức $P(x) = 5x^4 + 3x^5 - x^2 + 1$. Bậc của đa thức $P(x)$ là:
A. 2
B. 3
C. 4
D. 5

Câu 5. Thu nhập bình quân lao động của Việt Nam ở một số năm trong giai đoạn từ năm 2022 đến năm 2024, thống kê như sau.
| Nam | 2022 | 2023 | 2024 |
|---|---|---|---|
| Thu nhập (triệu đồng) | 6,7 | 7,3 | 7,7 |
Thu nhập bình quân lao động của Việt Nam ở năm 2024 tăng so với năm 2023 là khoảng
A. $105\%$
B. $5,4\%$
C. $5,47\%$
D. $5,48\%$

Câu 6. Một người đi bộ trong $x$ (giờ) với vận tốc $4$ (km/h) và sau đó đi bằng xe đạp trong $y$ (giờ) với vận tốc $18$ (km/h). Biểu thức đại số biểu thị tổng quãng đường đi được của người đó là:
A. $4(x+y)$
B. $22(x+y)$
C. $4y + 18x$
D. $4x + 18y$

Câu 7. Gieo ngẫu nhiên xúc xắc một lần. Xét biến cố 'Mặt xuất hiện của xúc xắc có số chấm là số chẵn'. Những kết quả thuận lợi cho biến cố trên là:
A. 2,3,4
B. 2,4,6
C. 2,4,5
D. 3,4,6

Câu 8. Chiều cao của mỗi bạn trong một tổ của lớp 7A được tổ trưởng thống kê như sau (theo đơn vị cm): 130, 135, 145, 200, 150. Dãy số liệu tổ trưởng liệt kê không hợp lí ở đâu?
A. 200
B. 150
C. 145
D. 130

Câu 9. Cho tam giác ABC, có $\hat{A} = 60^\circ$, $\hat{B} = 70^\circ$. Khi đó:
A. $AB > AC > BC$
B. $AB < AC < BC$
C. $AB > AC$
D. $AC > BC > AB$

Câu 10. Cho tam giác ABC có trung tuyến AM, điểm G là trọng tâm của tam giác. Khẳng định đúng là:
A. $\frac{AG}{AM} = \frac{2}{3}$
B. $\frac{AG}{GM} = \frac{2}{3}$
C. $\frac{AM}{AG} = \frac{2}{3}$
D. $\frac{GM}{AM} = \frac{2}{3}$

Câu 11. Độ dài hai cạnh của một tam giác là 1cm và 7cm. Trong các số đo sau, số đo nào sau đây là độ dài cạnh thứ 3 của tam giác?
A. 8cm
B. 9cm
C. 6cm
D. 7cm

Câu 1. Tâm của đường tròn ngoại tiếp của tam giác là giao của ba đường nào?
A. Ba đường trung tuyến
*B. Ba đường trung trực
C. Ba đường phân giác
D. Ba đường cao

Câu 2. Cho $\mathrm { P ( x ) } = 7 \mathrm { x } ^ { 4 } + 3 - 4 \mathrm { x } - 3 \mathrm { x } ^ { 2 } - 7 \mathrm { x } ^ { 4 } - \mathrm { x } + 5 \mathrm { x } ^ { 2 }$
*Đúng Thu gọn $\mathrm { P } ( \mathbf { x } )$ , được $\mathrm { P } ( \mathrm { x } ) = 2 \mathrm { x } ^ { 2 } - 5 \mathrm { x } + 3$
*Sai $\mathrm { P } ( - 2 ) = - 1$
*Đúng $\mathrm { P } ( \mathrm { x } )$ có bậc là 2
*Sai $\operatorname { P } ( \mathbf { x } ) : ( \mathbf { x } - 2 ) = 2 \mathbf { x } - 3$

Câu 3. Cho biết $\triangle ACB$ và $\triangle MNP$ có $\mathrm { \ A B = M N }$, $\mathrm { B C } = \mathrm { N P }$, ${ \sf A } { \sf C } = { \sf M } { \sf P }$ và ${ \widehat { \mathsf { B } } } = 6 5 ^ { \circ }$, $\hat { \mathsf C } = 5 5 ^ { 0 }$ Khi đó:
*Sai ${ \widehat { \sf B } } = { \widehat { P } }$
*Sai $\widehat { \mathrm { A } } = 6 5 ^ { 0 }$
*Đúng $\triangle ABC = \triangle MNP$ (c.c.c)
*Đúng $\widehat { \mathbb { M } } = 6 0 ^ { 0 }$

Câu 4: (0,75 điểm) Tính:
a) $- 2 x . ( x ^ { 2 } + 5 x - 1 )$
b) $\left( 6 x ^ { 2 } + 1 3 x - 5 \right) : ( 3 x - 1 )$

Câu 5: (1 điểm) Cho $\mathrm { A } ( \mathrm { x } ) = \mathrm { x } ^ { 4 } + 7 \mathrm { x } ^ { 3 } - 4 \mathrm { x } ^ { 2 } + 3 \mathrm { x } - \mathrm { 1 }$ $\mathrm { B } ( \mathrm { x } ) = \mathrm { \ x } ^ { 3 } - 4 \mathrm { x } ^ { 2 } - 5 \mathrm { x } + 1$
a) Tính $\operatorname { A } ( \mathrm { x } ) + \operatorname { B } ( \mathrm { x } )$
b) Tính $\mathrm { A } ( \mathrm { x } ) - \mathrm { B } ( \mathrm { x } )$

Câu 6: (0,75 điểm) Cho đa thức $P ( x ) = 2 x ^ { 4 } + 6 x - 3 x ^ { 5 } + 1$
a) Sắp xếp đa thức $\mathrm { P } ( x )$ theo số mũ giảm dần của biến.
b) Tìm bậc của đa thức $\mathrm { P } ( x )$
c) Tìm hệ số cao nhất, hệ số tự do của đa thức $\mathrm { P } ( x )$

Câu 7: (2 điểm) Cho $\triangle ABC$ vuông tại A, đường phân giác BE. Kẻ EH vuông góc với BC ( $\mathrm { H } \in \mathrm { B C }$ ). Gọi K là giao điểm của AB và HE. Chứng minh rằng:
a) $\Delta A B E = \Delta H B E$
b) BE là đường trung trực của đoạn thẳng AH.
c) ABKC cân

Câu 8: (0,5 điểm) Ba gia đình quyết định đào chung một cái giếng (hình vẽ). Phải chọn vị trí của giếng ở đâu để các khoảng cách từ giếng đến các nhà bằng nhau?
![](https://static-ai.hoclieu.vn/pdftoexcel/c6a94a04c14f43ff7c6c769f73e08e4280e65835b4e8ea88d7826ece69288f00.jpg)

Sử dụng dữ liệu sau để trả lời các câu hỏi 1; 2: Lượng bánh ngọt bán ra trong 1 ngày của một cửa hàng được biểu diễn bằng biểu đồ hình quạt tròn sau:
![](https://static-ai.hoclieu.vn/pdftoexcel/a865cb0aa207c1179a8c673b8a6dc84ce4c0e7c02e38b4f78b1a758890880b2f.jpg)

Câu 1. Tổng tỉ lệ phần trăm các loại bánh bán ra bằng $50\%$ là:
A. Bánh chuối, bánh quy và bánh donut.
B. Bánh mì, bánh donut và bánh kem.
C. Bánh kem và bánh quy.
D. Bánh chuối, bánh quy và bánh kem.

Câu 2. Tổng số tiền bán bánh của cửa hàng trong 1 ngày là 4 000 000 đồng. Số tiền bán bánh kem và bánh chuối trong ngày đó là
A. 640 000 đồng
B. 800 000 đồng
C. 1 440 000 đồng
D. 560 000 đồng

Câu 3. Cho ABC, các tia phân giác của góc B và C cắt nhau tại O. Qua O kẻ đường thẳng song song với BC cắt AB tại M, cắt AC tại N. Cho $\mathbf { BM } = 2 \mathbf { cm } ,$ $\mathrm { CN } = 3 \mathbf { cm }$ . Tính MN?
A. 5cm
B. 6cm
C. 7cm
D. 8cm

Câu 4. Biểu thức nào sau đây không là đa thức một biến?
A. `$\mathbf{x} + 5$`
B. `$\mathrm{y}^2 - \frac{3}{4}\mathrm{y} + 9$`
*C. `$\mathbf{x}^3 + \frac{2}{3\mathbf{x}} + 1$`
D. `2025x`

Câu 5. Trong $\triangle ABC$ có điểm I cách đều ba cạnh của tam giác. Khi đó điểm I là giao điểm của
A. Ba đường cao
B. Ba đường trung trực
C. Ba đường trung tuyến
D. Ba đường phân giác.

Câu 6. Một hộp có 10 quả bóng được đánh số từ 1 đến 10, đồng thời các quả bóng từ 1 đến 6 được sơn màu vàng và các quả bóng còn lại được sơn màu xanh, các quả bóng có kích thước và khối lượng như nhau. Lấy ngẫu nhiên một quả bóng trong hộp. Xác suất của biến cố "Quả bóng được chọn ra màu vàng và ghi số chẵn" là:
A. `$\frac{6}{10}$`
*B. `$\frac{3}{10}$`
C. `$\frac{1}{5}$`
D. `$\frac{2}{5}$`

Câu 7. Cho $\triangle ABC$, trung tuyến AM. Gọi G là trọng tâm của $\triangle ABC$ thì:
A. `$\frac{AG}{AM} = \frac{1}{3}$`
B. `$\frac{GM}{AM} = \frac{2}{3}$`
*C. `$\frac{GM}{AG} = \frac{1}{2}$`
D. `AM = 3AC`

Câu 8. Cho đa thức `$\mathbf{f}(\mathbf{x}) = \mathbf{ax}^2 + \mathbf{bx} + \mathbf{c}$` với a, b, c là các số thực, biết đa thức `$\mathbf{f}(\mathbf{x})$` chia hết cho đa thức `x - 1`. Giá trị của biểu thức `$\mathbf{S} = \mathbf{a} + \mathbf{b} + \mathbf{c}$` là:
A. `$\mathbf{S} = -1$`
*B. `$\mathbf{S} = 0$`
C. `$\mathbb{S} = 1$`
D. `S = 3`

Câu 9. Trong $\triangle MNP$ có điểm O cách đều ba đỉnh của tam giác. Khi đó điểm O là giao điểm của
A. Ba đường cao
B. Ba đường trung trực
C. Ba đường trung tuyến
D. Ba đường phân giác.

Câu 10. Viết ngẫu nhiên số tự nhiên có hai chữ số nhỏ hơn 50. Tập hợp các kết quả thuận lợi cho biến cố "số tự nhiên được viết ra có chữ số hàng đơn vị là 0" là
A. `{10; 20; 30; 40}`
B. `{20; 30; 40; 50}`
C. `{10; 20; 30; 40}`
D. `{20; 30; 40; 50}`

Câu 11. Cho tam giác ABC vuông tại B có `$\widehat{A} = 30^\circ$`, trên tia đối của tia BC lấy điểm E sao cho `BE = BC`. Khi đó tam giác ACE là tam giác:
A. Cân
B. Vuông cân
C. Vuông
D. Đều

Câu 12. Cho tam giác nhọn ABC có `$\widehat{B} < \widehat{C}$`, H là hình chiếu của A trên BC. Cách viết nào sau đây là đúng:
A. `$\mathrm{AB} > \mathrm{AC} > \mathrm{AH}$`
B. `$\mathrm{AB} > \mathrm{AH} > \mathrm{AC}$`
C. `$\mathrm{AC} > \mathrm{AB} > \mathrm{AH}$`
D. `$\mathrm{AC} > \mathrm{AH} > \mathrm{AB}$`

Câu 13. Cho hai đa thức: `P(x) = x^2 - 5x + 6` và `Q(x) = 3x + 12x^2 - 3x^5 - 13x^2 - 4`. Trong các khẳng định sau. Khẳng định nào đúng, khẳng định nào sai?
a) Đa thức Q(x) có bậc là 5, hệ số tự do là -4.
b) `$\mathbf{x} = 2$` và `$\mathbf{x} = -3$` là nghiệm của đa thức `$\mathbb{P}(\mathbf{x})$`.
c) `$\operatorname{P}(\mathbf{x}) + \operatorname{Q}(\mathbf{x}) = -5x + 2$`
d) Đa thức `$\sf{Q}(\mathbf{x})$` không có nghiệm.

Câu 14. Cho tam giác ABC cân tại A. Hai đường phân giác BM và CE cắt nhau tại I. Trong các khẳng định sau. Khẳng định nào đúng, khẳng định nào sai?
a) Điểm I cách đều ba đỉnh của tam giác ABC.
b) Tam giác IBC cân tại I.
c) `$\widehat{IAB} + \widehat{IBC} + \widehat{ICA} = 90^\circ$`.
d) Nếu `$\widehat{BAC} = 40^0$` thì `$\widehat{BIC} = 130^\circ$`.

Câu 15. (0,5 điểm) Biểu đồ cột (hình bên) biểu diễn số lượng vé bán được với các mức giá khác nhau của một buổi hòa nhạc: Hãy lập bảng thống kê biểu diễn số lượng vé bán được và cho biết vé bán được chiếm bao nhiêu phần trăm? Biết nhà hát có 2000 ghế.
![](https://static-ai.hoclieu.vn/pdftoexcel/8c3bc09223d3cc6e0556cf6ee0ea212a6e73d135a76e36b8789dd70e808e5756.jpg)

Câu 16. (1,0 điểm) Bạn Hà mở ngẫu nhiên một cuốn sách có 188 trang. Xét biến cố: Trang sách bạn Hà mở được là một số chia hết cho 3. Tính xác suất của biến cố đó.

Câu 17. (1,5 điểm)
a) Chứng tỏ giá trị của biểu thức sau không phụ thuộc vào biến `$\mathrm{A} = (\mathrm{x} - 2)(\mathrm{x}^2 + 2\mathrm{x} + 4) - \mathrm{x}(\mathrm{x}^2 - 5) + 1 - 5\mathrm{x}$`

Câu 17. (1,5 điểm)
a) Chứng tỏ giá trị của biểu thức sau không phụ thuộc vào biến $A=(x-2)(x^2+2x+4)-x(x^2-5)+1-5x$.
b) Tìm m sao cho $10x^2 - 7x + m$ chia cho $2x - 3$ có dư bằng 5.

Câu 18. (2,0 điểm) Cho tam giác ABC cân tại A. Kẻ BE vuông góc với AC tại E và CF vuông góc với AB tại F.
a) Chứng minh: $AE = AF$.
b) Gọi D là giao điểm của BE và CF, AD cắt BC tại H. Chứng minh AH là tia phân giác của góc BAC.
c) Lấy G là trung điểm của DB, CG cắt AH tại I. Chứng minh: $DI = 2IH$.
""".strip()

if __name__ == "__main__":
    result = markdown_to_json(markdown_content)
    print(json_module.dumps(result, ensure_ascii=False, indent=2))
    
    output_file = save_json_to_file(result)
    print(f"\nFile JSON đã được lưu tại: {output_file}")