import os
import json
import re
from tqdm import tqdm
from unidecode import unidecode
from urllib.parse import urljoin

from .utilities import format_filename, get_soup, get_pdf_text, create_script_dirs


def get_scriptsavant():
    ALL_URL = "https://thescriptsavant.com/movies.html"
    BASE_URL = "https://thescriptsavant.com/"
    SOURCE = "scriptsavant"
    DIR, TEMP_DIR, META_DIR = create_script_dirs(SOURCE)

    files = [os.path.join(DIR, f) for f in os.listdir(DIR) if os.path.isfile(
        os.path.join(DIR, f)) and os.path.getsize(os.path.join(DIR, f)) > 3000]

    metadata = {}
    soup = get_soup(ALL_URL)
    if soup is None:
        with open(os.path.join(META_DIR, SOURCE + ".json"), "w") as outfile:
            json.dump(metadata, outfile, indent=4)
        return

    movielist = []
    for movie in soup.find_all("a", href=True):
        href = movie.get("href")
        if not href or not href.lower().endswith(".pdf"):
            continue
        if "/movies/" not in href:
            continue
        movielist.append(movie)

    for movie in tqdm(movielist, desc=SOURCE):
        name = re.sub(r"\s+script\s*$", "", movie.get_text(" ", strip=True), flags=re.IGNORECASE).strip()
        file_name = format_filename(name)
        script_url = urljoin(BASE_URL, movie.get("href"))

        metadata[unidecode(name)] = {
            "file_name": file_name,
            "script_url": script_url
        }

        if os.path.join(DIR, file_name + '.txt') in files:
            continue

        try:
            text = get_pdf_text(script_url, os.path.join(SOURCE, file_name))

        except Exception as err:
            print(script_url)
            print(err)
            continue

        if text == "" or file_name == "":
            metadata.pop(unidecode(name), None)
            continue
        
        with open(os.path.join(DIR, file_name + '.txt'), 'w', errors="ignore") as out:
            out.write(text)

    with open(os.path.join(META_DIR, SOURCE + ".json"), "w") as outfile:
        json.dump(metadata, outfile, indent=4)
