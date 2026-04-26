import PyPDF2
reader = PyPDF2.PdfReader('CSC430_project_SP25_26.pdf')
text = '\n\n'.join([p.extract_text() for p in reader.pages])
with open('pdf_content.txt', 'w', encoding='utf-8') as f:
    f.write(text)
