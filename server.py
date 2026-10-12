from flask import Flask, render_template, jsonify, send_from_directory, request
import subprocess
import sys
import os
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime

# ---- Paths ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(BASE_DIR, "generated_pdfs")
os.makedirs(PDF_DIR, exist_ok=True)

# Server start time: used to ignore old files from previous runs
SERVER_START_TIME = datetime.now().timestamp()

# Unicode font registration (use Nirmala.ttc if present)
NIRMALA_FONT_NAME = "NirmalaUnicode"
NIRMALA_FONT_PATH = os.path.join(BASE_DIR, "Nirmala.ttc")
try:
    if os.path.exists(NIRMALA_FONT_PATH):
        pdfmetrics.registerFont(TTFont(NIRMALA_FONT_NAME, NIRMALA_FONT_PATH))
        print(f"[INFO] Registered Unicode font: {NIRMALA_FONT_PATH}")
    else:
        print("[WARN] Nirmala.ttc not found; PDF will use default font (Kannada/Hindi may not render).")
        NIRMALA_FONT_NAME = "Helvetica"
except Exception as e:
    print("[ERROR] Font registration failed:", e)
    NIRMALA_FONT_NAME = "Helvetica"

app = Flask(__name__, template_folder="templates", static_folder="static")


# ---------- Helpers ----------

def file_mtime(path):
    try:
        return os.path.getmtime(path)
    except Exception:
        return 0.0


def read_latest_from_excel(filename, columns_map):
    """
    filename: e.g. 'withdrawal_form.xlsx'
    columns_map: dict mapping desired keys -> excel column names
    returns (data_dict, mtime)
    """
    path = os.path.join(BASE_DIR, filename)
    m = file_mtime(path)
    if not os.path.exists(path) or m < SERVER_START_TIME:
        empty = {k: "" for k in columns_map.keys()}
        return empty, 0.0

    try:
        df = pd.read_excel(path)
        if df.empty:
            empty = {k: "" for k in columns_map.keys()}
            return empty, m
        last = df.iloc[-1]
        data = {}
        for key, col in columns_map.items():
            data[key] = last.get(col, "")
        return data, m
    except Exception as e:
        print(f"[ERROR] reading {filename}:", e)
        empty = {k: "" for k in columns_map.keys()}
        return empty, m


# attractive bank-slip style create_pdf_for_form function
def create_pdf_for_form(form_type, data, out_filename):
    """
    Attractive bank-slip style PDF generator.
    Uses NIRMALA_FONT_NAME for Unicode support.
    Looks best if you place a logo at static/logo.png.
    """
    from reportlab.lib import colors
    from reportlab.lib.utils import ImageReader
    from reportlab.graphics.barcode import qr as qrmod
    from reportlab.pdfbase.pdfmetrics import stringWidth

    c = canvas.Canvas(out_filename, pagesize=A4)
    w, h = A4

    # margins
    left = 36
    right = w - 36
    top = h - 36
    usable_w = right - left

    # header background
    header_h = 70
    c.setFillColor(colors.HexColor("#0b4da0"))   # deep bank blue
    c.rect(left, top - header_h, usable_w, header_h, fill=1, stroke=0)

    # logo (try loading static/logo.png)
    logo_path = os.path.join(BASE_DIR, "static", "logo.png")
    logo_size = 56
    logo_x = left + 12
    logo_y = top - header_h + (header_h - logo_size) / 2
    try:
        if os.path.exists(logo_path):
            img = ImageReader(logo_path)
            c.drawImage(img, logo_x, logo_y, width=logo_size, height=logo_size, mask='auto')
        else:
            # draw placeholder circle
            c.setFillColor(colors.white)
            c.circle(logo_x + logo_size / 2, logo_y + logo_size / 2, logo_size / 2, fill=1, stroke=0)
            c.setFillColor(colors.HexColor("#0b4da0"))
            c.setFont(NIRMALA_FONT_NAME, 18)
            c.drawCentredString(logo_x + logo_size/2, logo_y + logo_size/2 - 6, "AB")
    except Exception:
        pass

    # Bank name and branch in header (white)
    c.setFillColor(colors.white)
    bank_name = "RNSIT NATIONAL BANK"
    branch = "Main Branch - Banglore"
    c.setFont(NIRMALA_FONT_NAME, 18)
    c.drawString(logo_x + logo_size + 12, top - header_h/2 + 8, bank_name)
    c.setFont(NIRMALA_FONT_NAME, 10)
    c.drawString(logo_x + logo_size + 12, top - header_h/2 - 10, branch)

    # small subtle watermark diagonally
    c.saveState()
    c.translate(w/2, h/2)
    c.rotate(30)
    c.setFont(NIRMALA_FONT_NAME, 50)
    c.setFillColor(colors.HexColor("#e8eef7"))
    c.drawCentredString(0, 0, bank_name)
    c.restoreState()

    # Outer form box
    box_top = top - header_h - 16
    box_left = left
    box_width = usable_w
    box_height = 360
    c.setLineWidth(1)
    c.setStrokeColor(colors.HexColor("#0b4da0"))
    c.roundRect(box_left, box_top - box_height, box_width, box_height, 8, stroke=1, fill=0)

    # prepare positions for labels/fields (two-column layout)
    label_x = box_left + 18
    value_x = box_left + box_width/2
    y = box_top - 28
    row_gap = 28

    # small helper to draw label + value; supports long values by wrapping manually
    def draw_field(label, value, lbl_x=label_x, val_x=value_x, font_size=11):
        nonlocal y
        c.setFont(NIRMALA_FONT_NAME, font_size)
        c.setFillColor(colors.HexColor("#0b2b55"))
        c.drawString(lbl_x, y, label)
        c.setFillColor(colors.black)
        maxw = (box_left + box_width - val_x - 18)
        text_w = stringWidth(str(value), NIRMALA_FONT_NAME, font_size)
        if text_w <= maxw:
            c.drawString(val_x, y, str(value))
            y -= row_gap
        else:
            # wrap value into multiple lines
            words = str(value).split()
            line = ""
            line_y = y
            for wpart in words:
                trial = (line + " " + wpart).strip()
                if stringWidth(trial, NIRMALA_FONT_NAME, font_size) <= maxw:
                    line = trial
                else:
                    c.drawString(val_x, line_y, line)
                    line_y -= row_gap - 8
                    line = wpart
            c.drawString(val_x, line_y, line)
            y = line_y - row_gap

    # Title specific label sets
    if form_type == "withdrawal":
        c.setFont(NIRMALA_FONT_NAME, 13)
        c.setFillColor(colors.HexColor("#0b2b55"))
        c.drawString(box_left + 18, y, "WITHDRAWAL SLIP")
        y -= row_gap + 4

        draw_field("Date:", data.get("date", ""))
        draw_field("Account Holder Name:", data.get("name", ""))
        draw_field("Account Number:", data.get("account_no", ""))
        draw_field("PAN Number:", data.get("pan_no", ""))
        draw_field("Amount (₹):", data.get("amount", ""))
        y -= 8

        sig_y = box_top - box_height + 60
        c.setFont(NIRMALA_FONT_NAME, 10)
        c.drawString(box_left + box_width - 320, sig_y + 30, "Account Holder Signature")
        c.line(box_left + box_width - 320, sig_y + 18, box_left + box_width - 60, sig_y + 18)
        c.drawString(box_left + box_width - 320, sig_y - 10, "Bank Officer Signature")
        c.line(box_left + box_width - 320, sig_y - 22, box_left + box_width - 60, sig_y - 22)

    elif form_type == "deposit":
        c.setFont(NIRMALA_FONT_NAME, 13)
        c.setFillColor(colors.HexColor("#0b2b55"))
        c.drawString(box_left + 18, y, "DEPOSIT SLIP")
        y -= row_gap + 4

        draw_field("Date:", data.get("date", ""))
        draw_field("Depositor Name:", data.get("name", ""))
        draw_field("Account Number:", data.get("account_no", ""))
        draw_field("PAN Number:", data.get("pan_no", ""))
        draw_field("Amount (₹):", data.get("amount", ""))
        draw_field("Mode of Deposit:", data.get("mode", ""))
        y -= 4

        sig_y = box_top - box_height + 60
        c.drawString(box_left + box_width - 320, sig_y + 30, "Depositor Signature")
        c.line(box_left + box_width - 320, sig_y + 18, box_left + box_width - 60, sig_y + 18)
        c.drawString(box_left + box_width - 320, sig_y - 10, "Bank Officer Signature")
        c.line(box_left + box_width - 320, sig_y - 22, box_left + box_width - 60, sig_y - 22)

    else:  # cheque book
        c.setFont(NIRMALA_FONT_NAME, 13)
        c.setFillColor(colors.HexColor("#0b2b55"))
        c.drawString(box_left + 18, y, "CHEQUE BOOK REQUEST")
        y -= row_gap + 4

        draw_field("Date:", data.get("date", ""))
        draw_field("Account Holder Name:", data.get("name", ""))
        draw_field("Account Number:", data.get("account_no", ""))
        draw_field("PAN Number:", data.get("pan_no", ""))
        draw_field("No. of Cheque Leaves:", data.get("leaves", ""))

        c.setFont(NIRMALA_FONT_NAME, 9)
        dec_y = y
        c.drawString(box_left + 18, dec_y, "I request the bank to issue cheque book as per above particulars.")
        y -= row_gap + 10

        sig_y = box_top - box_height + 60
        c.drawString(box_left + box_width - 320, sig_y + 30, "Account Holder Signature")
        c.line(box_left + box_width - 320, sig_y + 18, box_left + box_width - 60, sig_y + 18)
        c.drawString(box_left + box_width - 320, sig_y - 10, "Bank Officer Signature")
        c.line(box_left + box_width - 320, sig_y - 22, box_left + box_width - 60, sig_y - 22)

    # small footer with date/time and reference id
    c.setFont(NIRMALA_FONT_NAME, 8)
    footer_text = f"Generated on {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
    c.setFillColor(colors.HexColor("#666666"))
    c.drawString(left + 10, 30, footer_text)

    # small placeholder QR (using data hash)
    try:
        qr_data = (bank_name + "|" + form_type + "|" + str(data.get("account_no","")) ).encode("utf-8")
        qr = qrmod.QrCodeWidget(qr_data)
        render_x = box_left + box_width - 90
        render_y = 32
        qr.drawOn(c, render_x, render_y)
    except Exception:
        pass

    c.showPage()
    c.save()

def remove_file_safe(filename):
    path = os.path.join(BASE_DIR, filename)
    try:
        if os.path.exists(path):
            os.remove(path)
        return True
    except Exception as e:
        print(f"[ERROR] removing {filename}:", e)
        return False


def clear_excel_with_columns(filename, columns):
    """
    Overwrite an Excel file with an empty DataFrame with the given columns.
    This preserves a file (but empty) so readers don't crash.
    """
    path = os.path.join(BASE_DIR, filename)
    try:
        df = pd.DataFrame(columns=columns)
        df.to_excel(path, index=False)
        return True
    except Exception as e:
        print(f"[ERROR] clearing {filename}:", e)
        return False


# ---------- Routes & API ----------

@app.route("/")
@app.route("/home")
def home():
    w_map = {"date": "Date", "name": "Account Holder Name", "account_no": "Account Number", "pan_no": "PAN Number", "amount": "Amount"}
    d_map = {"date": "Date", "name": "Depositor Name", "account_no": "Account Number", "pan_no": "PAN Number", "amount": "Amount", "mode": "Mode of Deposit"}
    c_map = {"date": "Date", "name": "Account Holder Name", "account_no": "Account Number", "pan_no": "PAN Number", "leaves": "Number of Cheque Leaves"}

    w_data, w_m = read_latest_from_excel("withdrawal_form.xlsx", w_map)
    d_data, d_m = read_latest_from_excel("deposit_form.xlsx", d_map)
    ch_data, ch_m = read_latest_from_excel("cheque_form.xlsx", c_map)

    initial_mtimes = {"withdrawal": w_m, "deposit": d_m, "cheque": ch_m}

    return render_template("home.html",
                           withdrawal=w_data,
                           deposit=d_data,
                           cheque=ch_data,
                           initial_mtimes=initial_mtimes)


@app.route("/start-assistant", methods=["POST"])
def start_assistant():
    try:
        python_exe = sys.executable
        script_path = os.path.join(BASE_DIR, "voice_assistant.py")
        if not os.path.exists(script_path):
            return jsonify({"status": "error", "message": "voice_assistant.py not found."}), 500
        subprocess.Popen([python_exe, script_path])
        return jsonify({"status": "started"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/latest-all")
def latest_all():
    w_map = {"date": "Date", "name": "Account Holder Name", "account_no": "Account Number", "pan_no": "PAN Number", "amount": "Amount"}
    d_map = {"date": "Date", "name": "Depositor Name", "account_no": "Account Number", "pan_no": "PAN Number", "amount": "Amount", "mode": "Mode of Deposit"}
    c_map = {"date": "Date", "name": "Account Holder Name", "account_no": "Account Number", "pan_no": "PAN Number", "leaves": "Number of Cheque Leaves"}

    w_data, w_m = read_latest_from_excel("withdrawal_form.xlsx", w_map)
    d_data, d_m = read_latest_from_excel("deposit_form.xlsx", d_map)
    ch_data, ch_m = read_latest_from_excel("cheque_form.xlsx", c_map)

    resp = {
        "withdrawal": {"mtime": w_m, "data": w_data},
        "deposit": {"mtime": d_m, "data": d_data},
        "cheque": {"mtime": ch_m, "data": ch_data}
    }
    return jsonify(resp)


@app.route("/download-withdrawal")
def download_withdrawal():
    data, m = read_latest_from_excel("withdrawal_form.xlsx",
                                     {"date":"Date","name":"Account Holder Name","account_no":"Account Number","pan_no":"PAN Number","amount":"Amount"})
    if m == 0.0:
        return jsonify({"status": "error", "message": "No recent withdrawal data"}), 400
    out = os.path.join(PDF_DIR, "withdrawal_details.pdf")
    create_pdf_for_form("withdrawal", data, out)
    return send_from_directory(PDF_DIR, "withdrawal_details.pdf", as_attachment=True)


@app.route("/download-deposit")
def download_deposit():
    data, m = read_latest_from_excel("deposit_form.xlsx",
                                     {"date":"Date","name":"Depositor Name","account_no":"Account Number","pan_no":"PAN Number","amount":"Amount","mode":"Mode of Deposit"})
    if m == 0.0:
        return jsonify({"status": "error", "message": "No recent deposit data"}), 400
    out = os.path.join(PDF_DIR, "deposit_details.pdf")
    create_pdf_for_form("deposit", data, out)
    return send_from_directory(PDF_DIR, "deposit_details.pdf", as_attachment=True)


@app.route("/download-cheque")
def download_cheque():
    data, m = read_latest_from_excel("cheque_form.xlsx",
                                     {"date":"Date","name":"Account Holder Name","account_no":"Account Number","pan_no":"PAN Number","leaves":"Number of Cheque Leaves"})
    if m == 0.0:
        return jsonify({"status": "error", "message": "No recent cheque data"}), 400
    out = os.path.join(PDF_DIR, "cheque_details.pdf")
    create_pdf_for_form("cheque", data, out)
    return send_from_directory(PDF_DIR, "cheque_details.pdf", as_attachment=True)


# ---------- Reset / Delete endpoints ----------

@app.route("/reset-withdrawal", methods=["POST"])
def reset_withdrawal():
    # Option: either delete file or write empty Excel with columns
    cols = ["Date", "Account Holder Name", "Account Number", "PAN Number", "Amount"]
    ok = clear_excel_with_columns("withdrawal_form.xlsx", cols)
    if not ok:
        return jsonify({"status":"error","message":"Failed to reset withdrawal file"}), 500
    return jsonify({"status":"ok"})


@app.route("/reset-deposit", methods=["POST"])
def reset_deposit():
    cols = ["Date", "Depositor Name", "Account Number", "PAN Number", "Amount", "Mode of Deposit"]
    ok = clear_excel_with_columns("deposit_form.xlsx", cols)
    if not ok:
        return jsonify({"status":"error","message":"Failed to reset deposit file"}), 500
    return jsonify({"status":"ok"})


@app.route("/reset-cheque", methods=["POST"])
def reset_cheque():
    cols = ["Date", "Account Holder Name", "Account Number", "PAN Number", "Number of Cheque Leaves"]
    ok = clear_excel_with_columns("cheque_form.xlsx", cols)
    if not ok:
        return jsonify({"status":"error","message":"Failed to reset cheque file"}), 500
    return jsonify({"status":"ok"})


@app.route("/reset-all", methods=["POST"])
def reset_all():
    r1 = clear_excel_with_columns("withdrawal_form.xlsx", ["Date", "Account Holder Name", "Account Number", "PAN Number", "Amount"])
    r2 = clear_excel_with_columns("deposit_form.xlsx", ["Date", "Depositor Name", "Account Number", "PAN Number", "Amount", "Mode of Deposit"])
    r3 = clear_excel_with_columns("cheque_form.xlsx", ["Date", "Account Holder Name", "Account Number", "PAN Number", "Number of Cheque Leaves"])
    if not (r1 and r2 and r3):
        return jsonify({"status":"error","message":"Failed to reset one or more files"}), 500
    return jsonify({"status":"ok"})


# 404 -> show homepage
@app.errorhandler(404)
def not_found(e):
    return home()


if __name__ == "__main__":
    print("[INFO] Starting Flask server...")
    app.run(host="0.0.0.0", port=5001, debug=True)
