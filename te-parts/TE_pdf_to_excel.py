import os
import re
import sys
import pandas as pd
from pathlib import Path

BASE_DIR = Path.cwd()   
INPUT_PATH = BASE_DIR / "PDFs"
OUTPUT_XLSX = BASE_DIR / "PDFs" / "te_pdf_details.xlsx"

def extract_text_from_pdf(pdf_path: str) -> str:
    text = ""
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
        if text.strip():
            return text
    except Exception:
        pass
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"
        if text.strip():
            return text
    except Exception:
        pass
    try:
        import fitz
        doc = fitz.open(pdf_path)
        for page in doc:
            text += (page.get_text() or "") + "\n"
        if text.strip():
            return text
    except Exception:
        pass

    raise RuntimeError(f"Could not extract text from {pdf_path} with available libraries.")

def _search(pattern, s, flags=re.I | re.S, default=""):
    m = re.search(pattern, s, flags)
    return (m.group(1).strip() if m else default).strip()

def _section_between(s: str, start_pat: str, end_pats):
    start = re.search(start_pat, s, flags=re.I | re.S)
    if not start:
        return ""
    start_idx = start.end()
    end_idx = len(s)
    for pat in end_pats:
        m = re.search(pat, s[start_idx:], flags=re.I | re.S)
        if m:
            end_idx = start_idx + m.start()
            break
    return s[start_idx:end_idx].strip()

def normalize_multiline(s: str) -> str:
    lines = [ln.rstrip() for ln in s.replace("\r", "\n").splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    out, empty = [], False
    for ln in lines:
        if ln.strip():
            out.append(ln)
            empty = False
        else:
            if not empty:
                out.append("")
            empty = True
    return "\n".join(out)

def remove_first_line_if_matches(block: str, patterns) -> str:
    block = normalize_multiline(block)
    lines = block.splitlines()
    if lines:
        head = lines[0].strip()
        for pat in patterns:
            if re.fullmatch(pat, head, flags=re.I):
                lines = lines[1:]
                break
    return "\n".join(lines).strip()

def parse_te_statement(text: str) -> dict:
    t = text.replace("\r", "\n")
    part_number = _search(r"TE\s*Internal\s*Number:\s*([^\n]+)", t)
    if not part_number:
        part_number = _search(r"Requested\s*Part.*?\b([0-9A-Za-z\-]+)\b", t)

    description = _search(r"Product\s*Description:\s*([^\n]+)", t)
    part_status = _search(r"Part\s*Status:\s*([^\n]+)", t)
    rohs = _section_between(
        t,
        r"EU\s*RoHS\s*Directive[^\n]*?:",
        [r"\n\s*EU\s*ELV\s*Directive\s*:", r"\n\s*EU\s*REACH\s*Regulation\s*:"]
    )
    elv_raw = _section_between(
        t,
        r"EU\s*ELV\s*Directive\s*:",
        [r"\n\s*China\s*RoHS.*?Directive\s*:", r"\n\s*EU\s*REACH\s*Regulation\s*:"]
    )
    elv = remove_first_line_if_matches(
        elv_raw,
        patterns=[r"2000/53/EC"]
    )

    reach_raw = _section_between(
        t,
        r"EU\s*REACH\s*Regulation\s*:",
        [r"\n\s*Halogen\s*Content\s*:"]
    )
    reach = remove_first_line_if_matches(
        reach_raw,
        patterns=[
            r"\(?EC\)?\s*No\.\s*1907/2006",
            r"EC\s*1907/2006",
            r"1907/2006"
        ]
    )
    halogen_block = _section_between(
        t,
        r"Halogen\s*Content\s*:\s*",
        [
            r"\n\s*Solder\s*Process\s*Capability\s*Code\s*:",
            r"\n\s*TE\s+Connectivity",
            r"\n\s*This\s+information\s+is\s+provided",
            r"\n\s*Page\s+\d+",
        ]
    )
    halogen = normalize_multiline(halogen_block)

    return {
        "Part Number (TE Internal #)": part_number,
        "TE Internal Description": description,
        "Part Status": part_status,
        "EU RoHS Directive 2011/65/EU": normalize_multiline(rohs),
        "EU ELV Directive 2000/53/EC": elv,
        "EU REACH Regulation (EC) No. 1907/2006": reach,
        "Halogen Content": halogen,
    }

def collect_pdfs(input_path: str):
    if os.path.isdir(input_path):
        pdfs = []
        for root, _, files in os.walk(input_path):
            for f in files:
                if f.lower().endswith(".pdf"):
                    pdfs.append(os.path.join(root, f))
        pdfs.sort()
        return pdfs
    return [input_path]

def write_excel(rows, out_xlsx: str):
    df = pd.DataFrame(rows, columns=[
        "Part Number (TE Internal #)",
        "TE Internal Description",
        "Part Status",
        "EU RoHS Directive 2011/65/EU",
        "EU ELV Directive 2000/53/EC",
        "EU REACH Regulation (EC) No. 1907/2006",
        "Halogen Content",
        "Source File",
    ])

    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Extract")
        ws = writer.sheets["Extract"]
        from openpyxl.styles import Alignment
        for col_idx, col in enumerate(df.columns, 1):
            max_len = max([len(str(x)) if pd.notnull(x) else 0 for x in [col] + df[col].tolist()])
            ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = min(max(12, int(max_len * 0.9)), 80)
            if "Directive" in col or "Regulation" in col or col == "Halogen Content":
                for r in range(2, len(df) + 2):
                    ws.cell(row=r, column=col_idx).alignment = Alignment(wrap_text=True, vertical="top")

def main():
    input_path = INPUT_PATH
    out_xlsx = OUTPUT_XLSX

    pdfs = collect_pdfs(input_path)
    if not pdfs:
        print(f"No PDFs found under: {input_path}")
        sys.exit(1)

    rows, errors = [], []
    for pdf in pdfs:
        try:
            txt = extract_text_from_pdf(pdf)
            row = parse_te_statement(txt)
            row["Source File"] = os.path.basename(pdf)
            rows.append(row)
        except Exception as e:
            errors.append((pdf, str(e)))

    write_excel(rows, out_xlsx)

    print(f"\nProcessed {len(rows)} file(s).")
    if errors:
        print("Completed with some errors:")
        for path, msg in errors:
            print(f"  - {path}: {msg}")
    print(f"Saved Excel to: {out_xlsx}")

if __name__ == "__main__":
    main()