import sys
from src.pipeline import process_statement

if __name__ == "__main__":
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "data/input_pdfs/statement.pdf"
    df, details = process_statement(pdf_path)
    print(details)
    print(df.head(20))