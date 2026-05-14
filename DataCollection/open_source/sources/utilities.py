from bs4 import BeautifulSoup
import subprocess
import time
import urllib.request
import string
import os
import textract
import re

HEADERS = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)'}
REQUEST_TIMEOUT = 120
REQUEST_RETRIES = 3


def format_filename(s):
    valid_chars = "-() %s%s%s" % (string.ascii_letters, string.digits, "%")
    filename = ''.join(c for c in s if c in valid_chars)
    filename = filename.replace('%20', ' ')
    filename = filename.replace('%27', '')
    filename = filename.replace(' ', '-')
    filename = re.sub(r'-+', '-', filename).strip()
    return filename


def get_soup(url):
    try:
        page = urllib.request.Request(url, headers=HEADERS)
        result = urllib.request.urlopen(page, timeout=REQUEST_TIMEOUT)
        resulttext = result.read()

        soup = BeautifulSoup(resulttext, 'html.parser')

    except Exception as err:
        print(err)
        soup = None
    return soup


def download_file(url, path):
    last_err = None
    for attempt in range(REQUEST_RETRIES):
        try:
            request = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as result:
                with open(path, 'wb') as f:
                    f.write(result.read())
            return
        except Exception as err:
            last_err = err
            if attempt < REQUEST_RETRIES - 1:
                time.sleep(2 * (attempt + 1))
    raise last_err


def decode_text(data):
    if isinstance(data, bytes):
        return data.decode('utf-8', errors='ignore')
    return data or ""


def extract_pdf_text(path):
    try:
        return decode_text(textract.process(path, encoding='utf-8'))
    except Exception as textract_err:
        try:
            return decode_text(textract.process(path))
        except Exception:
            try:
                result = subprocess.run(
                    ['pdftotext', '-enc', 'UTF-8', '-layout', path, '-'],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                return result.stdout.decode('utf-8', errors='ignore')
            except Exception:
                print(textract_err)
                return ""


def get_pdf_text(url, name):
    doc = os.path.join("scripts", "temp", name + ".pdf")
    os.makedirs(os.path.dirname(doc), exist_ok=True)
    try:
        download_file(url, doc)
        text = extract_pdf_text(doc)
    except Exception as err:
        print(err)
        text = ""
    # if os.path.isfile(doc):
    #     os.remove(doc)
    return text


def get_doc_text(url, name):
    doc = os.path.join("scripts", "temp", name + ".doc")
    os.makedirs(os.path.dirname(doc), exist_ok=True)
    try:
        download_file(url, doc)
        try:
            text = decode_text(textract.process(doc, encoding='utf-8'))
        except Exception:
            text = decode_text(textract.process(doc))
    except Exception as err:
        print(err)
        text = ""
    # if os.path.isfile(doc):
    #     os.remove(doc)
    return text


def create_script_dirs(source):
    DIR = os.path.join("scripts", "unprocessed", source)
    TEMP_DIR = os.path.join("scripts", "temp", source)
    META_DIR = os.path.join("scripts", "metadata")

    if not os.path.exists(DIR):
        os.makedirs(DIR)
    if not os.path.exists(META_DIR):
        os.makedirs(META_DIR)
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)

    return DIR, TEMP_DIR, META_DIR
