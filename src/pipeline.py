import os
from src.pdf_type_detector import detect_pdf_type
from src.text_extractor import extract_text_pdf
from src.ocr_extractor import extract_text_ocr
from src.parser import extract_account_details, extract_transactions
from src.classifier_rules import classify_rule_based
from src.classifier_ml import classify_ml
from src.exporter import export_to_csv, export_to_excel


def classify_transaction(description: str) -> str:
    return classify_rule_based(description) or safe_ml(description)


def safe_ml(description: str) -> str:
    try:
        return classify_ml(description)
    except Exception:
        return "Uncategorized"


def process_statement(pdf_path: str, out_dir: str = "data/output"):
    kind = detect_pdf_type(pdf_path)
    raw_text = extract_text_pdf(pdf_path) if kind == "text" else extract_text_ocr(pdf_path)

    account_details = extract_account_details(raw_text)
    df = extract_transactions(raw_text)

    if df.empty:
        raise ValueError(f"No transactions parsed from {pdf_path} (pdf_type={kind}). Check regex/template.")

    df["category"] = df["desc"].apply(classify_transaction)

    # Make sure the output directory actually exists (it won't on a fresh
    # clone / cloud deploy, since Git doesn't track empty folders).
    os.makedirs(out_dir, exist_ok=True)

    # os.path.basename works on both Windows ("\") and Linux ("/") paths;
    # a manual split("\\") silently fails on Linux temp paths and produces
    # a "base" that still contains slashes, which then gets treated as a
    # nested (nonexistent) subdirectory when writing the output file.
    base = os.path.basename(pdf_path)
    base = os.path.splitext(base)[0]

    export_to_csv(df, f"{out_dir}/{base}.csv")
    export_to_excel(df, f"{out_dir}/{base}.xlsx", account_details)

    return df, account_details
