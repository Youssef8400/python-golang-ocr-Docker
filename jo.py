import re
from datetime import datetime

class Document:
    def __init__(self, document_type, country_code, first_name, last_name, document_number, sex, birth_date, expire_date):
        self.document_type = document_type
        self.country_code = country_code
        self.first_name = first_name
        self.last_name = last_name
        self.document_number = document_number
        self.sex = sex
        self.birth_date = birth_date
        self.expire_date = expire_date

def parse_mrz(mrz_text):
    lines = mrz_text.split('\n')
    lines = [line.replace('\u003c', '<') for line in lines]

    if len(lines) < 2:
        raise ValueError("Invalid MRZ data: less than 2 lines")
    elif len(lines) == 2:
        return parse_passport(lines[0], lines[1])
    elif len(lines) == 3:
        return parse_id_card(lines[0], lines[1], lines[2])
    else:
        raise ValueError("Unknown MRZ format")

def parse_passport(line1, line2):
    document_type = my_trim(line1[0:2])
    country_code = my_trim(line1[2:5])
    names = line1[5:]
    first_name, last_name = get_names(names)  # Correct inversion ici
    document_number = my_trim(line2[0:9])
    sex_index = find_closest_sex(line2, 20)
    sex, birth_date, expire_date = None, None, None

    if sex_index != -1:
        sex = line2[sex_index]
        birth_date = stringify_date(line2[sex_index-7:sex_index-1], "birth")
        expire_date = stringify_date(line2[sex_index+1:sex_index+7], "expire")

    names = names.replace('<', ' ')
    return Document(document_type, country_code, first_name, last_name, document_number, sex, birth_date, expire_date)

def parse_id_card(line1, line2, line3):
    document_type = my_trim(line1[0:2])
    country_code = my_trim(line1[2:5])
    first_name, last_name = get_names(line3)  # Correct inversion ici
    document_number = get_cnie(line1)
    sex_index = find_closest_sex(line2, 7)
    sex, birth_date, expire_date = None, None, None

    if sex_index != -1:
        sex = line2[sex_index]
        birth_date = stringify_date(line2[sex_index-7:sex_index-1], "birth")
        expire_date = stringify_date(line2[sex_index+1:sex_index+7], "expire")

    return Document(document_type, country_code, first_name, last_name, document_number, sex, birth_date, expire_date)

def get_names(text):
    parts = text.split('<<')
    parts = [part for part in parts if part]
    last_name = parts[0].replace('<', ' ').strip() if parts else ""  # Nom de famille
    first_name = ' '.join(parts[1:]).replace('<', ' ').strip() if len(parts) > 1 else ""  # Prénom(s)
    return first_name, last_name  # Correct inversion ici

def stringify_date(text, date_type):
    if len(text) != 6:
        return "Invalid input length"

    year = int(text[:2])
    month = text[2:4]
    day = text[4:]

    current_year = datetime.now().year % 100

    if date_type == "expire":
        year += 2000
    elif date_type == "birth":
        year += 1900 if year > current_year else 2000

    return f"{day}/{month}/{year}"

def my_trim(input_str):
    return input_str.replace('<', ' ').strip()

def find_closest_sex(line, index):
    i, j = index, index
    while True:
        if i >= len(line) and j < 0:
            return -1
        if i < len(line) and line[i] in 'FM':
            return i
        if j >= 0 and line[j] in 'FM':
            return j
        i += 1
        j -= 1

def get_cnie(text):
    for i in range(len(text) - 1, -1, -1):
        if not text[i].isdigit() and text[i] != '<' and text[i] != ' ':
            return text[i:].replace('<', ' ').strip()
    return ""

import subprocess

def get_content(image):
    try:
        result = subprocess.run(['tesseract', image, 'stdout', '--psm', '6'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return result.stdout.decode('utf-8')
    except subprocess.CalledProcessError as e:
        return str(e)

class OCRAdapter:
    def parse_document(self, image):
        text = get_content(image)
        if not text:
            raise ValueError("OCR failed to extract content")

        mrz_text = [line.strip() for line in text.split('\n') if line.count('<') > 5]
        return parse_mrz('\n'.join(mrz_text))

def contains_multiple_less_than(line):
    return line.count('<') > 5

class APIPort:
    def get_document_data(self, filepath):
        adapter = OCRAdapter()
        return adapter.parse_document(filepath)

from fastapi import FastAPI, UploadFile, File, HTTPException

app = FastAPI()

@app.post("/get_document_data/")
async def get_document_data(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        with open("temp_image", "wb") as temp_file:
            temp_file.write(contents)
        
        api_port = APIPort()
        document = api_port.get_document_data("temp_image")
        
        return document.__dict__
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class OCRScannerPort:
    def parse_document(self, image):
        adapter = OCRAdapter()
        return adapter.parse_document(image)

