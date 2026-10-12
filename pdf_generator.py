from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from datetime import datetime

def generate_pdf(form_type, form_data):
    file_name = f"{form_type}_form_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf = canvas.Canvas(file_name, pagesize=A4)

    width, height = A4

    title = ""
    if form_type == "withdrawal":
        title = "WITHDRAWAL FORM"
    elif form_type == "deposit":
        title = "DEPOSIT FORM"
    else:
        title = "CHEQUE BOOK REQUEST FORM"

    # ---------- PDF HEADER ----------
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawCentredString(width / 2, height - 50, title)

    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, height - 90, f"Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
    pdf.line(50, height - 95, width - 50, height - 95)

    # ---------- FORM DATA ----------
    pdf.setFont("Helvetica", 14)
    y = height - 140

    for key, value in form_data.items():
        pdf.drawString(50, y, f"{key}:  {value}")
        y -= 40

        if y < 100:  # Add new page if long
            pdf.showPage()
            y = height - 80
            pdf.setFont("Helvetica", 14)

    pdf.save()
    return file_name
