import pandas as pd

def export_to_csv(df: pd.DataFrame, out_path: str):
    df.to_csv(out_path, index=False)

def export_to_excel(df: pd.DataFrame, out_path: str, account_details: dict | None = None):
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Transactions", index=False)
        if account_details:
            pd.DataFrame(account_details.items(), columns=["Field", "Value"]).to_excel(
                writer, sheet_name="Account Summary", index=False
            )
        # Category-wise totals as a quick pivot
        if "category" in df.columns:
            summary = df.groupby("category")[["debit", "credit"]].sum().reset_index()
            summary.to_excel(writer, sheet_name="Category Summary", index=False)