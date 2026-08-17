import streamlit as st
import tempfile, os
from src.pipeline import process_statement

st.title("Bank Statement Processor & Classifier")

uploaded = st.file_uploader("Upload a bank statement PDF", type="pdf")

if uploaded:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded.read())
        tmp_path = tmp.name

    with st.spinner("Processing..."):
        try:
            df, details = process_statement(tmp_path)
            st.success(f"Extracted {len(df)} transactions.")
            st.json(details)
            st.dataframe(df)

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("Download CSV", csv, "transactions.csv", "text/csv")

            base = os.path.basename(tmp_path).replace(".pdf", "")
            excel_path = f"data/output/{base}.xlsx"
            if os.path.exists(excel_path):
                with open(excel_path, "rb") as f:
                    excel_bytes = f.read()
                st.download_button(
                    "Download Excel",
                    excel_bytes,
                    "transactions.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            else:
                st.warning(f"Excel file not found at {excel_path} — check that data/output exists.")
        except Exception as e:
            st.error(f"Processing failed: {e}")
        finally:
            os.remove(tmp_path)