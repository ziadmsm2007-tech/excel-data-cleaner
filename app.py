"""Smart Data Cleaner

Flask web app: upload a messy Excel / CSV file and download a cleaned .xlsx file.
"""
import csv
import os
import re
from io import BytesIO, StringIO

import pandas as pd
from flask import Flask, render_template, request, send_file
from openpyxl.utils import get_column_letter

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
CSV_ENCODINGS = ("utf-8-sig", "cp1256")  # UTF-8 first, then Arabic Windows
MAX_UPLOAD_MB = 20
XLSX_MIMETYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024


def render_error(message, status=400):
    return render_template("index.html", error=message), status


@app.errorhandler(413)
def file_too_large(_error):
    return render_error(
        f"File is too large. Maximum size is {MAX_UPLOAD_MB} MB.", 413
    )


# ---------------------------------------------------------------- reading
def read_csv(raw):
    """Return {sheet_name: DataFrame} for a CSV file.

    Handles UTF-8 and Arabic (cp1256) encodings, and both "," and ";" separators.
    """
    for encoding in CSV_ENCODINGS:
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        try:
            df = pd.read_csv(StringIO(text), sep=None, engine="python")
        except (csv.Error, pd.errors.ParserError):
            df = pd.read_csv(StringIO(text))
        return {"Cleaned_Data": df}
    raise ValueError("Unsupported CSV encoding. Save the file as UTF-8.")


def read_excel(raw):
    """Return {sheet_name: DataFrame} for every sheet in the workbook."""
    return pd.read_excel(BytesIO(raw), sheet_name=None)


# --------------------------------------------------------------- cleaning
def tidy_text(value):
    """Trim, collapse repeated spaces, and turn blank text into an empty cell."""
    if not isinstance(value, str):
        return value
    value = re.sub(r"[ \t ]+", " ", value).strip()
    return value or None


def unique_names(names):
    """Make column names unique: Name, Name_1, Name_2 ..."""
    seen = {}
    result = []
    for name in names:
        if name in seen:
            seen[name] += 1
            result.append(f"{name}_{seen[name]}")
        else:
            seen[name] = 0
            result.append(name)
    return result


def clean_dataframe(df):
    df = df.copy()

    # 1. Standardize column headers
    headers = [" ".join(w.capitalize() for w in str(c).split()) for c in df.columns]
    df.columns = unique_names(headers)

    # 2. Trim extra spaces in text columns (blank text becomes an empty cell)
    for col in df.columns:
        series = df[col]
        if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
            df[col] = series.map(tidy_text)

    # 3. Drop completely empty rows, then 4. remove duplicates
    df = df.dropna(how="all").drop_duplicates().reset_index(drop=True)
    return df


# ---------------------------------------------------------------- writing
def build_workbook(sheets):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, df in sheets.items():
            sheet_name = str(name)[:31]
            df.to_excel(writer, index=False, sheet_name=sheet_name)
            ws = writer.sheets[sheet_name]
            ws.freeze_panes = "A2"
            for position, col in enumerate(df.columns, start=1):
                values = df[col].head(1000).dropna()
                longest = max([len(str(col))] + [len(str(v)) for v in values])
                ws.column_dimensions[get_column_letter(position)].width = min(
                    longest + 2, 50
                )
    output.seek(0)
    return output


# ----------------------------------------------------------------- routes
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html")

    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return render_error("No file uploaded.")

    stem, ext = os.path.splitext(os.path.basename(uploaded.filename))
    if ext.lower() not in ALLOWED_EXTENSIONS:
        return render_error(
            "Unsupported file format. Please upload a CSV or Excel file."
        )

    raw = uploaded.read()
    try:
        sheets = read_csv(raw) if ext.lower() == ".csv" else read_excel(raw)
        cleaned = {name: clean_dataframe(df) for name, df in sheets.items()}
    except Exception:
        app.logger.exception("Failed to process %s", uploaded.filename)
        return render_error(
            "Could not read this file. Make sure it is a valid, non-empty "
            "Excel or CSV file."
        )

    if all(df.empty for df in cleaned.values()):
        return render_error("The file has no data left after cleaning.")

    return send_file(
        build_workbook(cleaned),
        download_name=f"cleaned_{stem}.xlsx",
        as_attachment=True,
        mimetype=XLSX_MIMETYPE,
    )


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
