import sys, os, traceback
sys.path.insert(0, '.')
from src.text_extractor import extract_text_pdf
from src.parser import extract_transactions, extract_account_details

path = r'data\input_pdfs\Kotak_Bank_Sample_Statement.pdf'

text = extract_text_pdf(path)
df = extract_transactions(text)
print('Rows from extract_transactions:', len(df))
print(df.head())
print()

print('--- trying full pipeline ---')
try:
    from src.pipeline import process_statement
    df2, details = process_statement(path)
    print('Pipeline succeeded, rows:', len(df2))
except Exception:
    traceback.print_exc()
