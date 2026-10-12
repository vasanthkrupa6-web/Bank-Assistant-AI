# Bank Assistant AI

An AI-powered banking assistant designed to make banking interactions easier through voice interaction and automated bank form filling.

## Overview

Bank Assistant AI helps users interact with a banking application using voice-based input and assists in filling banking forms. The project combines Python, web technologies, and PDF generation to simplify common banking tasks.

## Features

- Voice-based interaction with the banking assistant
- Automated filling of banking forms
- PDF generation for completed forms
- Web interface for interacting with the application
- Support for withdrawal and other banking form workflows

## Technologies Used

- **Programming Language:** Python
- **Backend:** Flask
- **Frontend:** HTML, CSS, JavaScript
- **Document Processing:** PDF generation and form filling
- **Data Handling:** Excel files and form templates

## Project Structure

```text
Bank-Assistant-AI/
├── server.py
├── voice_assistant.py
├── form_filler.py
├── form_pdf_creator.py
├── pdf_generator.py
├── static.ini
├── pdf_templates/
├── static/
├── templates/
└── README.md
```

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/vasanthkrupa6-web/Bank-Assistant-AI.git
cd Bank-Assistant-AI
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it on Windows:

```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

Install the Python packages required by the project. Once the dependencies are listed in `requirements.txt`, run:

```bash
pip install -r requirements.txt
```

### 4. Run the application

```bash
python server.py
```

Open the local address displayed in the terminal in your web browser.

## Project Goal

The goal of Bank Assistant AI is to simplify banking interactions by combining voice assistance, web-based workflows, and automated form generation.

## Future Enhancements

- Improve voice recognition and natural-language understanding
- Add support for more banking forms and workflows
- Improve accessibility and multilingual interaction
- Strengthen input validation and security

## Author

**Krupa Vasanth**

GitHub: [vasanthkrupa6-web](https://github.com/vasanthkrupa6-web)

---

*This project is intended as an educational demonstration. Do not use real banking credentials or sensitive customer data for testing.*