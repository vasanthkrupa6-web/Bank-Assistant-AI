# voice_assistant.py
#
# Voice-only bank form assistant with Kannada-number → digit conversion.
# Minimal fix: ensure_full_account_number listens a few extra times when detected digits are short.

import os
import sys
import time
import re
import tempfile
from datetime import datetime

import speech_recognition as sr
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play
import pandas as pd

# Optional path (unused directly here)
INDIC_TTS_PATH = r"C:\Users\krupa\OneDrive\Desktop\Indic-Tts"

# ---------- Configure FFmpeg paths ----------
FFMPEG_PATH = r"C:\Users\krupa\Downloads\ffmpeg-8.0-essentials_build\ffmpeg-8.0-essentials_build\bin\ffmpeg.exe"
FFPROBE_PATH = r"C:\Users\krupa\Downloads\ffmpeg-8.0-essentials_build\ffmpeg-8.0-essentials_build\bin\ffprobe.exe"
AudioSegment.converter = FFMPEG_PATH
AudioSegment.ffprobe = FFPROBE_PATH
os.environ["PATH"] += os.pathsep + os.path.dirname(FFMPEG_PATH)

# ---------- TTS temp folder ----------
TTS_TEMP_DIR = os.path.join(os.path.expanduser("~"), "voice_assistant_tts")
os.makedirs(TTS_TEMP_DIR, exist_ok=True)


# ---------------- Kannada number parsing utilities ----------------

_KAN_NUM = {
    "ಸೊನ್ನೆ": 0, "ಶೂನ್ಯ": 0, "೦": 0,
    "ಒಂದು": 1, "ಒರ": 1, "ಒರೇ": 1, "ಒನ್": 1, "ondu": 1, "one": 1,
    "ಎರಡು": 2, "రెడు": 2, "eradu": 2, "two": 2, "2": 2,
    "ಮೂರು": 3, "ಮೂಡು": 3, "muru": 3, "three": 3,
    "ನಾಲ್ಕು": 4, "naalku": 4, "four": 4,
    "ಐದು": 5, "aidu": 5, "five": 5,
    "ಆರು": 6, "aaru": 6, "six": 6,
    "ಏಳು": 7, "elu": 7, "seven": 7,
    "ಎಂಟು": 8, "entu": 8, "eight": 8,
    "ಒಂಬತ್ತು": 9, "ombattu": 9, "nine": 9,
    "ಹತ್ತು": 10, "hattu": 10, "ten": 10,
    "ಹನ್ನೊಂದು": 11, "ಹನ್ನೆರಡು": 12,
    "ಇಪ್ಪತ್ತು": 20, "ippattu": 20,
    "ಮಪ್ಪತ್ತು": 30, "mappattu": 30,
    "ನಲವತ್ತು": 40, "nalavattu": 40,
    "ಐವತ್ತು": 50, "aivattu": 50,
    "ಅರವತ್ತು": 60, "aravattu": 60,
    "ಎಪ್ಪತ್ತು": 70, "eppattu": 70,
    "ಎಂಬತ್ತು": 80, "embuattu": 80,
    "ತೊಂಬತ್ತು": 90, "tombattu": 90,
    "ನೂರು": 100, "nuru": 100,
    "ಶತ": 100,
    "ಸಾವಿರ": 1000, "saavira": 1000, "thousand": 1000,
    "ಲಕ್ಷ": 100000, "lakh": 100000,
}

_EXTRA_MAP = {}
for k, v in list(_KAN_NUM.items()):
    _EXTRA_MAP[k.lower()] = v
_KAN_NUM.update(_EXTRA_MAP)

_KANNADA_DIGIT_OFFSET = ord("\u0CE6")
def convert_kannada_digits(s: str) -> str:
    out_chars = []
    for ch in s:
        code = ord(ch)
        if 0x0CE6 <= code <= 0x0CEF:
            out_chars.append(str(code - _KANNADA_DIGIT_OFFSET))
        else:
            out_chars.append(ch)
    return "".join(out_chars)

def kannada_words_to_number(text: str):
    """
    Fix: If user speaks digit-by-digit (one two three…), concatenate → 123.
    If user speaks big numbers (one thousand two hundred…), use multiplier logic.
    """

    if not text or not isinstance(text, str):
        return None

    s = convert_kannada_digits(text.strip().lower())

        # If ASCII digits are present, concatenate all digit runs into one number.
    # This handles cases like "1 2 3 4" (recognizer returns spaced digits).
    digit_runs = re.findall(r"\d+", s)
    if digit_runs:
        # join all runs: "1", "2", "3" -> "123"
        try:
            return int("".join(digit_runs))
        except Exception:
            # fallback to first run if something odd happens
            return int(digit_runs[0])


    # Tokenize
    tokens = re.split(r"[\s,.-]+", s)
    tokens = [t for t in tokens if t]

    values = []
    for tk in tokens:
        if tk in _KAN_NUM:
            values.append(_KAN_NUM[tk])
        else:
            # try simplified version (remove vowels)
            t_simple = tk.replace("ಾ", "").replace("ಿ", "").replace("ು", "")
            if t_simple in _KAN_NUM:
                values.append(_KAN_NUM[t_simple])

    if not values:
        return None

    # -------------------------------------------------------------
    # ⭐ FIX: If ALL values are single digits → concatenate
    # -------------------------------------------------------------
    if all(0 <= v <= 9 for v in values):
        # Example: [1,2,3,4] -> "1234"
        return int("".join(str(v) for v in values))

    # -------------------------------------------------------------
    # Otherwise use multiplier logic for big numbers
    # -------------------------------------------------------------
    total = 0
    current = 0

    for v in values:
        if v >= 100:
            if current == 0:
                current = 1
            current *= v
        else:
            current += v

        if v >= 1000:
            total += current
            current = 0

    total += current
    return total


def normalize_numeric_field(captured_text: str):
    if not captured_text:
        return captured_text
    txt = convert_kannada_digits(captured_text.strip())
    num = kannada_words_to_number(txt)
    if num is not None:
        return str(num)
        # As fallback, extract/concatenate all digit runs (handles "1 2 3 4")
    digit_runs = re.findall(r"\d+", txt)
    if digit_runs:
        return "".join(digit_runs)

    return captured_text


# --------- helper: ensure_full_account_number (silently append digits) ----------
def ensure_full_account_number(initial_text: str, listen_lang_code: str, min_length: int = 10, max_tries: int = 4):
    """
    Use initial_text (first recognition). If the normalized digits appear shorter than min_length,
    silently listen up to max_tries additional times and append any digits found.
    """
    if not initial_text:
        digits = ""
    else:
        digits = normalize_numeric_field(initial_text)
        if digits and not digits.isdigit():
            m = re.search(r"\d+", digits)
            digits = m.group(0) if m else ""
    if isinstance(digits, str) and len(digits) >= min_length:
        return digits
    tries = 0
    while tries < max_tries and (not digits or len(digits) < min_length):
        tries += 1
        more = listen(listen_lang_code, timeout=6, phrase_time_limit=6)
        if not more:
            continue
        more_digits = normalize_numeric_field(more)
        if more_digits and isinstance(more_digits, str):
            md = re.search(r"\d+", more_digits)
            add = md.group(0) if md else ""
            if add:
                digits += add
    if not digits:
        return normalize_numeric_field(initial_text) if initial_text else ""
    return digits


# -------------------------- TTS --------------------------
def speak(text: str, lang: str):
    tmp_mp3 = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3", dir=TTS_TEMP_DIR) as f:
            tmp_mp3 = f.name
        tts = gTTS(text=text, lang=lang)
        tts.save(tmp_mp3)
        sound = AudioSegment.from_file(tmp_mp3, format="mp3")
        play(sound)
    except Exception as e:
        print("TTS/playback error:", e)
    finally:
        try:
            if tmp_mp3 and os.path.exists(tmp_mp3):
                os.remove(tmp_mp3)
        except Exception:
            pass


# ---------- Utility: listen (SpeechRecognition) ----------
def listen(lang_code="en-IN", timeout=12, phrase_time_limit=12):
    r = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            print("🎤 Listening...")
            r.adjust_for_ambient_noise(source, duration=0.8)
            audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        try:
            text = r.recognize_google(audio, language=lang_code)
            print("👉 You said:", text)
            return text.lower()
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            print("Speech service error:", e)
            return ""
    except Exception as e:
        print("Microphone/listen error:", e)
        return ""


# ---------- Ask until valid ----------
def ask_until_valid(question_text: str, lang_for_tts: str, listen_lang_code: str):
    while True:
        speak(question_text, lang_for_tts)
        text = listen(listen_lang_code)
        if text and text.strip():
            return text.strip()
        time.sleep(0.3)


# ---------- Mapping helpers ----------
def is_withdrawal_word(recognized: str):
    if not recognized:
        return False
    recognized = recognized.lower()
    keywords = ["ಹಣ", "ತೆಗೆಯ", "ತೆಗೆಯು", "निकासी", "withdraw", "withdrawal", "withdrawl"]
    return any(k in recognized for k in keywords)

def is_deposit_word(recognized: str):
    if not recognized:
        return False
    recognized = recognized.lower()
    keywords = ["ಜಮಾ", "deposit", "जमा", "jama"]
    return any(k in recognized for k in keywords)

def is_cheque_word(recognized: str):
    if not recognized:
        return False
    recognized = recognized.lower()
    keywords = ["ಚೆಕ್", "ಪುಸ್ತಕ", "cheque", "check", "चेक"]
    return any(k in recognized for k in keywords)


# ---------- Form handlers ----------
def handle_withdrawal(lang_code_short, listen_lang_code):
    today = datetime.now().strftime("%d-%m-%Y")
    form = {"Date": today}
    if lang_code_short == "kn":
        questions = [
            ("Account Holder Name", "ಹೆಸರು ಹೇಳಿ."),
            ("Account Number", "ಖಾತೆ ನಂಬರ ಹೇಳಿ."),
            ("PAN Number", "ಪ್ಯಾನ್ ನಂಬರ ಹೇಳಿ."),
            ("Amount", "ಮೊತ್ತ ಹೇಳಿ."),
        ]
    elif lang_code_short == "hi":
        questions = [
            ("Account Holder Name", "नाम बताएं।"),
            ("Account Number", "खाता संख्या बताएं।"),
            ("PAN Number", "पैन नंबर बताएं।"),
            ("Amount", "राशि बताएं।"),
        ]
    else:
        questions = [
            ("Account Holder Name", "Please say account holder name."),
            ("Account Number", "Please say account number."),
            ("PAN Number", "Please say PAN number."),
            ("Amount", "Please say the amount."),
        ]

    for key, q in questions:
        answer = ask_until_valid(q, lang_code_short, listen_lang_code)
        if key == "Account Number":
            answer = ensure_full_account_number(answer, listen_lang_code, min_length=10, max_tries=4)
        elif key == "Amount":
            # Amounts can be multi-word; try to ensure reasonable length too (min_length=1 but allow multi listens)
            answer = ensure_full_account_number(answer, listen_lang_code, min_length=1, max_tries=3)
        form[key] = answer

    save_form("withdrawal_form.xlsx", form, lang_code_short)


def handle_deposit(lang_code_short, listen_lang_code):
    today = datetime.now().strftime("%d-%m-%Y")
    form = {"Date": today}
    if lang_code_short == "kn":
        questions = [
            ("Depositor Name", "ಹೆಸರು ಹೇಳಿ."),
            ("Account Number", "ಖಾತೆ ನಂಬರ ಹೇಳಿ."),
            ("PAN Number", "ಪ್ಯಾನ್ ನಂಬರ ಹೇಳಿ."),
            ("Amount", "ಮೊತ್ತ ಹೇಳಿ."),
            ("Mode of Deposit", "ಹಣ ಅಥವಾ ಚೆಕ್ ಎಂದು ಹೇಳಿ."),
        ]
    elif lang_code_short == "hi":
        questions = [
            ("Depositor Name", "नाम बताएं।"),
            ("Account Number", "खाता संख्या बताएं।"),
            ("PAN Number", "पैन नंबर बताएं।"),
            ("Amount", "राशि बताएं।"),
            ("Mode of Deposit", "नकद या चेक कहें।"),
        ]
    else:
        questions = [
            ("Depositor Name", "Please say depositor name."),
            ("Account Number", "Please say account number."),
            ("PAN Number", "Please say PAN number."),
            ("Amount", "Please say the amount."),
            ("Mode of Deposit", "Say Cash or Cheque."),
        ]

    for key, q in questions:
        answer = ask_until_valid(q, lang_code_short, listen_lang_code)
        if key == "Account Number":
            answer = ensure_full_account_number(answer, listen_lang_code, min_length=10, max_tries=4)
        elif key == "Amount":
            answer = ensure_full_account_number(answer, listen_lang_code, min_length=1, max_tries=3)
        form[key] = answer

    save_form("deposit_form.xlsx", form, lang_code_short)


def handle_cheque(lang_code_short, listen_lang_code):
    today = datetime.now().strftime("%d-%m-%Y")
    form = {"Date": today}
    if lang_code_short == "kn":
        questions = [
            ("Account Holder Name", "ಹೆಸರು ಹೇಳಿ."),
            ("Account Number", "ಖಾತೆ ನಂಬರ ಹೇಳಿ."),
            ("PAN Number", "ಪ್ಯಾನ್ ನಂಬರ ಹೇಳಿ."),
            ("Number of Cheque Leaves", "ಚೆಕ್ ಪುಟಗಳ ಸಂಖ್ಯೆ ಹೇಳಿ."),
        ]
    elif lang_code_short == "hi":
        questions = [
            ("Account Holder Name", "नाम बताएं।"),
            ("Account Number", "खाता संख्या बताएं।"),
            ("PAN Number", "पैन नंबर बताएं।"),
            ("Number of Cheque Leaves", "कितने पन्ने चाहिए बताएं।"),
        ]
    else:
        questions = [
            ("Account Holder Name", "Please say account holder name."),
            ("Account Number", "Please say account number."),
            ("PAN Number", "Please say PAN number."),
            ("Number of Cheque Leaves", "Please say number of cheque leaves required."),
        ]

    for key, q in questions:
        answer = ask_until_valid(q, lang_code_short, listen_lang_code)
        if key == "Account Number":
            answer = ensure_full_account_number(answer, listen_lang_code, min_length=10, max_tries=4)
        elif key == "Number of Cheque Leaves":
            answer = normalize_numeric_field(answer)
        form[key] = answer

    save_form("cheque_form.xlsx", form, lang_code_short)


# ---------- Save form to excel (openpyxl) or CSV fallback ----------
def save_form(file_name, form_dict, lang_code_short):
    for numeric_key in ("Amount", "Number of Cheque Leaves", "Account Number"):
        if numeric_key in form_dict:
            form_dict[numeric_key] = normalize_numeric_field(form_dict[numeric_key])

    df = pd.DataFrame([form_dict])
    csv_name = file_name.replace(".xlsx", ".csv")
    used_file = None

    try:
        df_existing = None
        if os.path.exists(file_name):
            try:
                df_existing = pd.read_excel(file_name)
            except Exception:
                df_existing = None
        if df_existing is not None:
            df = pd.concat([df_existing, df], ignore_index=True)
        df.to_excel(file_name, index=False)
        used_file = file_name
    except Exception as e:
        print("Excel save error, falling back to CSV:", e)
        try:
            if os.path.exists(csv_name):
                df_existing = pd.read_csv(csv_name)
                df = pd.concat([df_existing, df], ignore_index=True)
            df.to_csv(csv_name, index=False)
            used_file = csv_name
        except Exception as e2:
            print("Failed to save form at all:", e2)
            return

    print(f"Saved: {used_file}")
    if lang_code_short == "kn":
        speak("ಫಾರ್ಮ್ ಸೇಫ್ ಆಗಿದೆ.", "kn")
    elif lang_code_short == "hi":
        speak("फॉर्म सेव हो गया है।", "hi")
    else:
        speak("Form has been saved.", "en")


# ---------- MAIN flow ----------
def main():
    while True:
        speak("Namaskara! Namaste! Hello! Say Kannada, Hindi or English.", "en")
        lang_choice = listen("en-IN")
        if not lang_choice:
            continue
        lang_choice = lang_choice.lower()
        if "kannad" in lang_choice or "ಕನ್ನಡ" in lang_choice:
            lang_short = "kn"
            listen_lang = "kn-IN"
            speak("ನೀವು ಕನ್ನಡ ಆಯ್ಕೆಮಾಡಿದ್ದೀರಿ.", "kn")
            break
        elif "hindi" in lang_choice or "हिन्दी" in lang_choice or "हिंदी" in lang_choice:
            lang_short = "hi"
            listen_lang = "hi-IN"
            speak("आपने हिंदी चुनी है।", "hi")
            break
        elif "english" in lang_choice or "ಇಂಗ್ಲೀಷ್" in lang_choice or "अंग्रेज़ी" in lang_choice:
            lang_short = "en"
            listen_lang = "en-IN"
            speak("You selected English.", "en")
            break
        else:
            continue

    while True:
        if lang_short == "kn":
            speak("ದಯವಿಟ್ಟು ಫಾರ್ಮ್ ಹೇಳಿ: ಹಣ ತೆಗೆಯು, ಜಮಾ ಅಥವಾ ಚೆಕ್ ಪುಸ್ತಕ.", "kn")
        elif lang_short == "hi":
            speak("कृपया फॉर्म बोलें: निकासी, जमा, या चेक बुक।", "hi")
        else:
            speak("Please say form type: Withdrawal, Deposit, or Cheque Book.", "en")

        form_answer = listen(listen_lang)
        if not form_answer:
            continue

        if is_withdrawal_word(form_answer):
            form_type = "withdrawal"
            break
        elif is_deposit_word(form_answer):
            form_type = "deposit"
            break
        elif is_cheque_word(form_answer):
            form_type = "cheque"
            break
        else:
            continue

    if form_type == "withdrawal":
        handle_withdrawal(lang_short, listen_lang)
    elif form_type == "deposit":
        handle_deposit(lang_short, listen_lang)
    elif form_type == "cheque":
        handle_cheque(lang_short, listen_lang)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
