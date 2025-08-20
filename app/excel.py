import pandas as pd

def toExcel(data, image_urls_map=None, output_path="output.xlsx"):
    columns = [
        'Câu hỏi', 'Loại câu hỏi', 'Độ khó (Mặc định: Nhận biết)', 'Trộn lựa chọn (Mặc định: Có)',
        *[f"Lựa chọn {i}" for i in range(1, 11)],
        'Đáp án', 'Đúng', 'Sai',
        *[f"Vế {side} {i}" for i in range(1, 11) for side in ("trái", "phải")],
        *[f"Cột {side} {i}" for i in range(1, 11) for side in ("trái", "phải")],
        'Đáp án nối', 'Giải thích', "Ảnh minh họa"
    ]

    header_desc = [f"({col})" for col in columns]

    type_map = {
        "multiple_choice": "Trắc nghiệm 1 đáp án (Multiple Choice)",
        "checkbox": "Trắc nghiệm nhiều đáp án (Checkbox)",
        "essay": "Tự luận (Essay)",
        "fill_in_blank": "Điền khuyết (Fill In)",
        "true_false": "Đúng sai (True False)",
        "matching_single": "Nối 1 đáp án (Matching 1 answer)",
        "matching_multiple": "Nối nhiều đáp án (Matching multi-answer)",
        "ordering": "Sắp xếp (Order items)",
        "image": "Ảnh minh họa (Image)"
    }

    def safe_int(val, default=1):
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    def get_choice_list(options, max_len=10):
        return [options[i] if options and i < len(options) and options[i] else "lỗi không lấy được đáp án" for i in range(max_len)]

    rows = []
    for item in data:
        qtype = item.get("Question type", "").strip()
        row = [""] * len(columns)

        # Basic info
        row[0] = item.get("Question", "")
        row[1] = type_map.get(qtype, qtype)
        row[2] = item.get("Difficulty level", "Nhận biết (Remembering)")
        row[3] = "Có (Yes)"
        row[-1] = image_urls_map.get(item.get("image", ""), item.get("image", "")) if image_urls_map else item.get("image", "")

        if qtype in ("Multiple Choice", "multiple_choice"):
            row[4:14] = get_choice_list(item.get("options", []), 10)
            row[14] = safe_int(item.get("answer", 1))

        elif qtype in ("Checkbox", "checkbox"):
            row[4:14] = get_choice_list(item.get("options", []), 10)
            answers = item.get("answer", [1,2,3])
            row[14] = ",".join(map(str, answers))

        elif qtype in ("True False", "true_false"):
            statements = item.get("statements", [])
            row[14] = ""  # Answers not needed
            row[15] = ",".join(str(i+1) for i, s in enumerate(statements) if s.get("answer"))
            row[16] = ",".join(str(i+1) for i, s in enumerate(statements) if not s.get("answer"))
            for i, s in enumerate(statements):
                if i < 10:
                    row[4+i] = s.get("text", "")

        elif qtype in ("Fill In", "fill_in_blank", "Essay", "essay"):
            row[25] = ""  # Giải thích

        elif qtype in ("Order items", "ordering"):
            items_list = item.get("items", [])
            for i, it in enumerate(items_list[:10]):
                row[4+i] = it

        elif qtype in ("Matching 1 answer", "Matching multi-answer", "matching_single", "matching_multiple"):
            left, right = item.get("left", []), item.get("right", [])
            if len(left) == len(right):
                row[1] = "Nối 1 đáp án (Matching 1 answer)"
                for i, (l,r) in enumerate(zip(left,right)):
                    if i < 10:
                        row[20 + 2*i] = l
                        row[21 + 2*i] = r
            else:
                row[1] = "Nối nhiều đáp án (Matching multi-answer)"
                for i, l in enumerate(left[:10]):
                    row[40+i] = l
                for i, r in enumerate(right[:10]):
                    row[50+i] = r
            if "match" in item:
                row[54] = "\\n".join(f"{k} -> {v}" for k,v in item["match"].items())

        rows.append(row)

    df = pd.DataFrame([header_desc] + rows, columns=columns)
    df.to_excel(output_path, index=False)

