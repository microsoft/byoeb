import os
import PyPDF2

def convert_pdf_to_txt(pdf_path, txt_path):
    # Open the PDF file in read-binary mode
    with open(pdf_path, 'rb') as pdf_file:
        # Create a PDF file reader object
        pdf_reader = PyPDF2.PdfReader(pdf_file)

        # Initialize an empty string to hold the extracted text
        text = ''

        # Loop through each page in the PDF and extract the text
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += page.extract_text()

    # Write the extracted text to the output text file
    with open(txt_path, 'w') as txt_file:
        txt_file.write(text)

pdf_folder_path = os.path.join(os.environ['APP_PATH'], os.environ['DATA_PATH'], 'raw_documents_pdf')
txt_folder_path = os.path.join(os.environ['APP_PATH'], os.environ['DATA_PATH'], 'raw_documents')

os.makedirs(txt_folder_path, exist_ok=True)

for pdf_file_name in os.listdir(pdf_folder_path):
    pdf_file_path = os.path.join(pdf_folder_path, pdf_file_name)
    txt_file_path = os.path.join(txt_folder_path, pdf_file_name.replace('.pdf', '.txt'))
    convert_pdf_to_txt(pdf_file_path, txt_file_path)