from flask import Flask, render_template, request 

#Flask: Handles the web app (routing, file uploads).
#os: For file and folder path handling.
#json/csv: To save extracted data in standard formats.
#spacy: NLP library to extract names, orgs, dates, etc.
#docx: To read .docx resumes.
#re: Regular expressions for emails and phone numbers.

import os
import json
import csv
import spacy
import docx
import re


#UPLOAD_FOLDER: Where user resumes are saved temporarily.
#OUTPUT_FOLDER: Where we store CSV/JSON outputs.
#os.makedirs(..., exist_ok=True): Ensures folders exist (creates if not).
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Load spaCy model
# Loads the small English model from spaCy that can detect names, organizations, locations, and dates from raw text.
nlp = spacy.load("en_core_web_sm")


#Checks file type and extracts text:
#For .pdf — uses pdfplumber to get text from each page.
#For .docx — uses python-docx to get paragraphs.
#Returns the combined plain text from the file.
def extract_text_from_file(file_path):
    if file_path.endswith('.pdf'):
        from pdfplumber import open as pdf_open
        with pdf_open(file_path) as pdf:
            return ''.join(page.extract_text() or '' for page in pdf.pages)
    elif file_path.endswith('.docx'):
        doc = docx.Document(file_path)
        return '\n'.join([para.text for para in doc.paragraphs])
    else:
        return None

#Uses spaCy's nlp() to analyze text and extract:
#Name: First detected PERSON entity.
#Organizations: All unique ORG entities (e.g., companies, schools).
#Dates: All date mentions.
#Locations: All geographic names (GPE = Geo-Political Entity).
#Email and Phone: Handled by regex functions.

def extract_entities(text):
    doc = nlp(text)
    return {
        'Name': next((ent.text for ent in doc.ents if ent.label_ == "PERSON"), "Not Found"),
        'Email': extract_email(text),
        'Phone': extract_phone(text),
        'Organizations': list(set(ent.text for ent in doc.ents if ent.label_ == "ORG")),
        'Dates': list(set(ent.text for ent in doc.ents if ent.label_ == "DATE")),
        'Locations': list(set(ent.text for ent in doc.ents if ent.label_ == "GPE")),
    }

def extract_email(text):
    match = re.search(r'[\w\.-]+@[\w\.-]+', text)
    return match.group(0) if match else "Not Found"

def extract_phone(text):
    match = re.search(r'\+?\d[\d\s\-]{7,}\d', text)
    return match.group(0) if match else "Not Found"
 
 #Creates two files: <filename>.json and <filename>.csv inside /output/.
 #Uses:
 #json.dump() to write a structured version.
 #csv.DictWriter() to write a flat row.

def save_data(data, filename_prefix):
    # Save as JSON
    with open(os.path.join(OUTPUT_FOLDER, f'{filename_prefix}.json'), 'w') as jf:
        json.dump(data, jf, indent=4)
    # Save as CSV
    with open(os.path.join(OUTPUT_FOLDER, f'{filename_prefix}.csv'), 'w', newline='') as cf:
        writer = csv.DictWriter(cf, fieldnames=data.keys())
        writer.writeheader()
        writer.writerow(data)

#Shows the resume upload form from your upload.html.
@app.route('/')
def upload_form():
    return render_template('upload.html')


# Checks if a file was submitted.
# Saves the file to /uploads.
# Extracts text using the earlier helper function.
# Uses spaCy + regex to extract data from that text.
# Saves the data as .json and .csv.
# Shows results in the browser and confirms that the files were saved.
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'resume' not in request.files:
        return 'No file part'
    file = request.files['resume']
    if file.filename == '':
        return 'No selected file'

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)

    text = extract_text_from_file(file_path)
    if not text:
        return 'Unsupported file format or no text found'

    data = extract_entities(text)
    save_data(data, os.path.splitext(file.filename)[0])

    return f"""
    <h3>Extracted Resume Data:</h3>
    <pre>{json.dumps(data, indent=4)}</pre>
    <p>✅ Data saved as CSV and JSON in <code>/output</code> folder.</p>
    """

#Runs the Flask app on localhost:5000 with debug mode on (so you see live errors).
if __name__ == '__main__':
    app.run(debug=True)
