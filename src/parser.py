

import re
import pandas as pd


# Date patterns


# DD-MM-YYYY / DD/MM/YYYY / DD/MM/YY, and "DD Mon YYYY" (SBI-style).
DATE_TOKEN = r"\d{2}[-/]\d{2}[-/]\d{2,4}|\d{2}\s+[A-Za-z]{3,9}\s+\d{4}"
DATE_TOKEN_RE = re.compile(DATE_TOKEN)
LINE_STARTS_WITH_DATE = re.compile(
    r"^(?:\d{1,4}\s+)?(" + DATE_TOKEN + r")"  # optional leading serial no. (ICICI)
)

AMOUNT_RE = re.compile(r"\d[\d,]*\.\d{2}")

DATE_FORMATS = [
    "%d-%m-%Y", "%d-%m-%y",
    "%d/%m/%Y", "%d/%m/%y",
    "%d %b %Y", "%d %B %Y",
]


def _parse_date(s: str):
    s = s.strip()
    for fmt in DATE_FORMATS:
        try:
            return pd.to_datetime(s, format=fmt)
        except (ValueError, TypeError):
            continue
    return pd.to_datetime(s, errors="coerce", dayfirst=True)



# Line-level junk filtering (headers / footers / metadata that repeat on
# every page and would otherwise get swept up as "orphan" description text)


_HEADER_KEYWORDS = [
    "ACCOUNT NAME", "ACCOUNT NO", "ACCOUNT NUMBER", "ACCOUNT TYPE",
    "ACCOUNT DESCRIPTION", "ADDRESS", "BRANCH", "IFSC", "IFS CODE", "MICR",
    "CIF", "CURRENCY", "STATEMENT PERIOD", "STATEMENT FROM", "STATEMENT TO",
    "STATEMENT OF ACCOUNT", "ACCOUNT STATEMENT", "STATEMENT OF ACCOUNT",
    "PERIOD :", "NOMINATION", "PRODUCT", "CUSTOMER NAME",
    "OPENING BALANCE", "CLOSING BALANCE",
    "THIS IS A", "SAMPLE/TEST", "SAMPLE STATEMENT", "TESTING PURPOSES",
    "TXN DATE", "TRAN DATE", "VALUE DATE", "TRANSACTION DATE",
    "DESCRIPTION", "PARTICULARS", "NARRATION", "TRANSACTION REMARKS",
    "DEBIT", "CREDIT", "WITHDRAWAL", "DEPOSIT", "BALANCE",
    "CHQ", "REF NO", "REF.NO", "CHEQUE", "INIT. BR", "INIT.BR",
    "(DR)", "(CR)", "STATEMENT OF",
]

# Short, isolated header fragments produced by column-wrapped table headers
# (e.g. SBI's "Ref" / "No." / "No", ICICI's "S.N ..." / "o Date No (Dr)",
# HDFC's "Withdrawal" / "Amt.")
_SHORT_JUNK_TOKENS = {"REF", "NO.", "NO", "O", "AMT.", "AMT"}


def _is_junk_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    upper = stripped.upper()
    bare = upper.strip(".:")
    if bare in _SHORT_JUNK_TOKENS:
        return True
    for kw in _HEADER_KEYWORDS:
        if kw in upper:
            return True
    # Bank-name-only title lines, e.g. "AXIS BANK", "HDFC BANK",
    # "Kotak Mahindra Bank", "State Bank of India", "ICICI Bank"
    if re.fullmatch(r"[A-Za-z .]+ ?(BANK|BANK LTD\.?)", stripped, re.IGNORECASE):
        return True
    return False


def _looks_like_continuation(line: str) -> bool:
    """A short, all-word fragment with no digits — plausible wrapped
    description text (e.g. 'ELECTRICITY', 'BANGALORE', 'MERCHANT')."""
    stripped = line.strip()
    if not stripped or _is_junk_line(stripped):
        return False
    if AMOUNT_RE.search(stripped):
        return False
    if LINE_STARTS_WITH_DATE.match(stripped):
        return False
    words = stripped.split()
    return 1 <= len(words) <= 6 and all(re.match(r"^[A-Za-z/&.\-]+$", w) for w in words)


# Matches the first "numeric tail" token in a line: either a run of 4+
# digits (a ref/cheque number) or a decimal amount. Used to find the
# boundary between description words and the ref/amount/balance columns.
_NUMERIC_TAIL_RE = re.compile(r"\d{4,}|\d[\d,]*\.\d{2}")

_LEAD_DATES_RE = re.compile(
    r"^(?:\d{1,4}\s+)?(?:" + DATE_TOKEN + r")(?:\s+(?:" + DATE_TOKEN + r"))?"
)


def normalize_lines(raw_text: str) -> list:
    """Turn raw extracted text into a list of clean, logically-complete
    transaction-line strings, with headers/footers stripped and wrapped
    description fragments reattached to the transaction row they belong
    to.

    Wrapped descriptions can appear as a fragment BEFORE the numeric row
    (prefix, e.g. SBI's "TRANSFER TO/FROM BESCOM" on its own line before
    the date/ref/amount row) and/or AFTER it (suffix, e.g. "ELECTRICITY"
    on the line following). Crucially, a row's OWN description is only
    treated as wrapped-away (and thus eligible to pull in prefix/suffix
    fragments) when there is no description text already sitting between
    the date and the first ref/amount number on that row — otherwise a
    prefix fragment meant for the *next* row gets mis-attached as a
    suffix of the current, already-complete row.
    """
    raw_lines = raw_text.split("\n")
    n = len(raw_lines)

    merged = []
    pending_prefix = []
    i = 0
    while i < n:
        line = raw_lines[i].strip()
        if not line:
            i += 1
            continue

        if LINE_STARTS_WITH_DATE.match(line):
            lead_m = _LEAD_DATES_RE.match(line)
            lead = lead_m.group(0)
            rest = line[len(lead):].strip()
            tail_m = _NUMERIC_TAIL_RE.search(rest)
            if tail_m:
                mid_desc = rest[: tail_m.start()].strip()
                tail = rest[tail_m.start():]
            else:
                mid_desc = rest
                tail = ""

            if not mid_desc:
                # Description fully wrapped away onto neighboring lines.
                prefix_text = " ".join(pending_prefix)
                pending_prefix = []

                j = i + 1
                suffix_words = []
                # Cap at a single fragment: observed statements only ever
                # wrap one trailing word onto the next physical line. A
                # second consecutive continuation-shaped line is actually
                # the *prefix* of the following transaction's description
                # (e.g. "TRANSFER TO/FROM ...") and must not be consumed
                # here, or it gets duplicated/misattached.
                if j < n and _looks_like_continuation(raw_lines[j]):
                    suffix_words.append(raw_lines[j].strip())
                    j += 1

                desc_full = " ".join(w for w in [prefix_text] + suffix_words if w)
                full = (lead + " " + desc_full + " " + tail).strip()
                merged.append(full)
                i = j
            else:
                # Row already has its own description text — it's
                # complete. Any pending prefix wasn't meant for this row
                # (it belongs to whatever transaction comes next, if any).
                pending_prefix = []
                merged.append(line)
                i += 1
        else:
            if _is_junk_line(line):
                i += 1
                continue
            if AMOUNT_RE.search(line):
                # A stray line with numbers but no leading date — not a
                # description continuation; ignore rather than mis-merge.
                i += 1
                continue
            # Plausible prefix continuation for an upcoming transaction row.
            pending_prefix.append(line)
            i += 1

    return merged


def normalize_text(raw_text: str) -> str:
    """Kept for backward compatibility / direct text use: returns the
    normalized lines rejoined as text."""
    return "\n".join(normalize_lines(raw_text))


# ---------------------------------------------------------------------------
# Account details
# ---------------------------------------------------------------------------

def extract_account_details(text: str) -> dict:
    details = {}
    patterns = {
        "bank_name": r"^([A-Z][A-Za-z .&]*?(?:BANK|Bank)[A-Za-z .&]*)\b",
        "account_name": r"(?:Account Name|Customer Name|Name)\s*:\s*(.+?)(?:\s{2,}|\n|$)",
        "account_number": r"Account No[a-z.:]*\s*:?\s*(\d+)",
        "ifsc": r"IFS[C]?\s*Code?\s*:?\s*([A-Z0-9]+)|IFSC\s*:\s*([A-Z0-9]+)",
        "micr": r"MICR(?:\s*Code)?\s*:\s*(\d+)",
        "branch": r"Branch(?:\s*Name)?\s*:\s*(.+?)(?:\s{2,}|\n|$)",
        "cif": r"CIF\s*No\.?\s*:\s*(\d+)",
        "account_type": r"Account Type\s*:\s*([A-Za-z /\-]+?)(?:\s{2,}|\n|$)",
        "period": r"(?:Statement Period|Period)\s*:?\s*([\d/\- A-Za-z]+?)\s+to\s+([\d/\- A-Za-z]+)",
    }
    for key, pat in patterns.items():
        m = re.search(pat, text, re.MULTILINE)
        if m:
            groups = [g for g in m.groups() if g]
            if len(groups) == 1:
                details[key] = groups[0].strip()
            elif len(groups) > 1:
                details[key] = tuple(g.strip() for g in groups)

    opening = re.search(r"Opening Balance\s*:?\s*([\d,]+\.\d{2})", text)
    closing = re.search(r"Closing Balance\s*:?\s*([\d,]+\.\d{2})", text)
    if opening:
        details["opening_balance"] = float(opening.group(1).replace(",", ""))
    if closing:
        details["closing_balance"] = float(closing.group(1).replace(",", ""))

    return details


def detect_bank(text: str) -> str:
    upper = text.upper()
    if "KOTAK" in upper:
        return "KOTAK"
    if "AXIS BANK" in upper:
        return "AXIS"
    if "HDFC" in upper:
        return "HDFC"
    if "ICICI" in upper:
        return "ICICI"
    if "STATE BANK OF INDIA" in upper or re.search(r"\bSBI\b", upper):
        return "SBI"
    return "GENERIC"


# ---------------------------------------------------------------------------
# Per-bank line templates
#
# Each template is applied to a single *normalized* line (wrapped fragments
# already reattached, headers already stripped) and must expose:
#   date, desc, ref (optional), and the trailing amount tokens ending in
#   balance. Debit/credit split is intentionally NOT decided here — it's
#   derived later from the balance delta, which is robust to column-order
#   differences and OCR misalignment across banks.
# ---------------------------------------------------------------------------

BANK_TEMPLATES = {
    "KOTAK": re.compile(
        r"^(?P<date>\d{2}-\d{2}-\d{4})\s+"
        r"(?P<desc>.+?)\s+"
        r"(?P<ref>\d{6,})\s+"
        r"(?P<amt>[\d,]+\.\d{2})\s+"
        r"(?P<balance>[\d,]+\.\d{2})\s*$"
    ),
    "AXIS": re.compile(
        r"^(?P<date>\d{2}-\d{2}-\d{4})\s+-\s+"
        r"(?P<desc>.+?)\s+"
        r"(?P<amt>[\d,]+\.\d{2})\s+"
        r"(?P<balance>[\d,]+\.\d{2})"
        r"(?:\s+\d{2,6})?\s*$"  # trailing branch/init code
    ),
    "HDFC": re.compile(
        r"^(?P<date>\d{2}/\d{2}/\d{2})\s+"
        r"(?P<desc>.+?)\s+"
        r"(?P<ref>\d{6,})\s+"
        r"(?P<valdate>\d{2}/\d{2}/\d{2})\s+"
        r"(?P<amt>[\d,]+\.\d{2})\s+"
        r"(?P<balance>[\d,]+\.\d{2})\s*$"
    ),
    "ICICI": re.compile(
        r"^(?:(?P<sno>\d{1,4})\s+)?"
        r"(?P<date>\d{2}/\d{2}/\d{4})\s+"
        r"(?P<valdate>\d{2}/\d{2}/\d{4})\s+"
        r"(?P<ref>\d{3,})\s+"
        r"(?P<desc>.+?)\s+"
        r"(?P<amt1>[\d,]+\.\d{2}|-)\s+"
        r"(?P<amt2>[\d,]+\.\d{2}|-)\s+"
        r"(?P<balance>[\d,]+\.\d{2})\s*$"
    ),
    "SBI": re.compile(
        r"^(?P<date>\d{2}\s+[A-Za-z]{3}\s+\d{4})\s+"
        r"(?P<valdate>\d{2}\s+[A-Za-z]{3}\s+\d{4})\s+"
        r"(?P<desc>.+?)\s+"
        r"(?P<ref>\d{6,})\s+"
        r"(?P<amt>[\d,]+\.\d{2})\s+"
        r"(?P<balance>[\d,]+\.\d{2})\s*$"
    ),
}

# Generic fallback for banks without a dedicated template above. Handles a
# single date, an optional ref number, one amount, and a balance.
GENERIC_TEMPLATE = re.compile(
    r"^(?P<date>" + DATE_TOKEN + r")\s+"
    r"(?:" + DATE_TOKEN + r"\s+)?"        # optional second (value) date
    r"(?P<desc>.+?)\s+"
    r"(?:(?P<ref>\d{6,})\s+)?"
    r"(?P<amt>[\d,]+\.\d{2})\s+"
    r"(?P<balance>[\d,]+\.\d{2})\s*$"
)

REF_HASH_RE = re.compile(r"REF#(\d+)")


def _clean_amount(token: str):
    if token is None or token == "-":
        return None
    return float(token.replace(",", ""))


def _parse_line(bank: str, line: str):
    """Return dict(date, desc, ref, amount, balance) or None if the line
    doesn't match the expected transaction shape for this bank."""
    template = BANK_TEMPLATES.get(bank, GENERIC_TEMPLATE)
    m = template.match(line)
    if not m:
        # Fall back to the generic template if the bank-specific one fails
        # on an unexpected row (e.g. a format variant).
        if template is not GENERIC_TEMPLATE:
            m = GENERIC_TEMPLATE.match(line)
        if not m:
            return None

    gd = m.groupdict()
    desc = gd.get("desc", "").strip()
    ref = gd.get("ref")

    # Axis-style ref is embedded in the description as "REF#12345678".
    if not ref:
        rm = REF_HASH_RE.search(desc)
        if rm:
            ref = rm.group(1)
            desc = REF_HASH_RE.sub("", desc).strip()

    # ICICI-style: two amount columns, one of which is "-".
    if "amt1" in gd:
        amt = _clean_amount(gd.get("amt1")) or _clean_amount(gd.get("amt2"))
    else:
        amt = _clean_amount(gd.get("amt"))

    balance = _clean_amount(gd.get("balance"))
    if amt is None or balance is None:
        return None

    return {
        "date": gd["date"],
        "desc": re.sub(r"\s{2,}", " ", desc).strip(" -"),
        "ref": ref or "",
        "amount": amt,
        "balance": balance,
    }


def extract_transactions(text: str, bank: str = None) -> pd.DataFrame:
    if bank is None:
        bank = detect_bank(text)

    lines = normalize_lines(text)

    rows = []
    for line in lines:
        parsed = _parse_line(bank, line)
        if parsed:
            rows.append(parsed)

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["balance"] = df["balance"].astype(float)
    df["amount"] = df["amount"].astype(float)
    df["date"] = df["date"].apply(_parse_date)

    # Keep original statement order (do NOT sort by date — same-day
    # transactions must stay in balance order for the delta method below;
    # statements are already chronological top-to-bottom).
    df = df.reset_index(drop=True)

    df["debit"] = 0.0
    df["credit"] = 0.0
    prev_balance = None
    for i, row in df.iterrows():
        if prev_balance is not None:
            diff = round(row["balance"] - prev_balance, 2)
            if diff < 0:
                df.at[i, "debit"] = round(-diff, 2)
            else:
                df.at[i, "credit"] = round(diff, 2)
        else:
            # First row: infer from whether it's plausible the amount was
            # a debit or credit by comparing amount to the diff magnitude;
            # since we have no prior balance, trust the parsed amount sign
            # is unknowable from balance alone, so fall back to marking it
            # using the parsed 'amount' vs whichever direction matches an
            # opening-balance-consistent guess is handled by the caller
            # (process_statement) if opening_balance is available.
            pass
        prev_balance = row["balance"]

    df["flagged"] = False

    return df[["date", "desc", "ref", "debit", "credit", "balance", "flagged"]]


def reconcile_with_opening_balance(df: pd.DataFrame, opening_balance: float) -> pd.DataFrame:
    """Fill in debit/credit for the first row (which has no prior balance
    to diff against) using the statement's stated opening balance, and
    flag any row where the running balance doesn't reconcile."""
    if df.empty or opening_balance is None:
        return df

    df = df.copy()
    first_balance = df.loc[0, "balance"]
    diff = round(first_balance - opening_balance, 2)
    if diff < 0:
        df.at[0, "debit"] = round(-diff, 2)
    else:
        df.at[0, "credit"] = round(diff, 2)

    prev_balance = opening_balance
    for i, row in df.iterrows():
        expected = round(prev_balance - row["debit"] + row["credit"], 2)
        if abs(expected - row["balance"]) > 0.01:
            df.at[i, "flagged"] = True
        prev_balance = row["balance"]

    return df
