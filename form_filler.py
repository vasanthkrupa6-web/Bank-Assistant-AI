from fpdf import FPDF
import os

def fill_pdf(data, output_file="filled_bank_form.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="BANK FORM", ln=1, align="C")

    pdf.ln(10)

    for key, value in data.items():
        pdf.cell(200, 10, txt=f"{key}: {value}", ln=1)

    pdf.output(output_file)
    print(f"PDF saved as {output_file}")

    return output_file
