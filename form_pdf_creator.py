# form_pdf_creator.py

import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 👉 Updated font to TTC file
FONT_PATH = os.path.join(BASE_DIR, "Nirmala.ttc")

try:
    pdfmetrics.registerFont(TTFont("Nirmala", FONT_PATH))
    KANNADA_FONT = "Nirmala"
    print("✔ Kannada font loaded successfully!")
except Exception as e:
    print("[FONT WARNING] Could not load Nirmala font, fallback to Helvetica:", e)
    KANNADA_FONT = "Helvetica"


def create_withdrawal_details_pdf(data: dict) -> str:
    """
    Create a simple PDF with withdrawal details using Unicode Kannada-capable font.
    """
    out_path = os.path.join(BASE_DIR, "withdrawal_details.pdf")

    c = canvas.Canvas(out_path, pagesize=A4)
    width, height = A4

    # Title
    c.setFont(KANNADA_FONT, 18)
    c.drawString(80, height - 100, "Bank Withdrawal Details")

    c.setFont(KANNADA_FONT, 13)

    def write(label, key, y):
        value = str(data.get(key, "") or "")
        c.drawString(80, y, f"{label}: {value}")

    write("Date", "date", height - 150)
    write("Account Holder Name", "name", height - 180)
    write("Account Number", "account_no", height - 210)
    write("PAN Number", "pan_no", height - 240)
    write("Amount", "amount", height - 270)

    c.showPage()
    c.save()
    return out_path
