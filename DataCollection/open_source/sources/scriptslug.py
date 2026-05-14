import os
import re
import json
import urllib.request

from tqdm import tqdm
from .utilities import format_filename, get_soup, get_pdf_text, create_script_dirs


def get_scriptslug():
    SITEMAP_URL = "https://www.scriptslug.com/sitemap-scripts.xml"
    SOURCE = "scriptslug"
    DIR, TEMP_DIR, META_DIR = create_script_dirs(SOURCE)

    def get_script_from_url(script_url, file_name):
        text = ""

        try:
            text = get_pdf_text(script_url, os.path.join(SOURCE, file_name))
            return text

        except Exception as err:
            print(script_url)
            print(err)
            text = ""

        return text

    def get_script_pages():
        request = urllib.request.Request(
            SITEMAP_URL,
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"},
        )
        with urllib.request.urlopen(request) as response:
            xml = response.read().decode("utf-8", errors="ignore")
        return re.findall(r"<loc>(.*?)</loc>", xml)

    def get_script_details(script_page_url):
        script_soup = get_soup(script_page_url)
        if script_soup is None:
            return None

        if script_soup.find("a", href="/scripts/format/film") is None:
            return None

        read_link = script_soup.find(
            "a",
            href=lambda href: href is not None and ".pdf" in href.lower(),
        )
        if read_link is None:
            return None

        header = script_soup.find("h1")
        if header is None:
            return None

        name = header.get_text(" ", strip=True)
        file_name = re.sub(r"\([^)]*\)", "", format_filename(name))
        script_url = read_link.get("href")
        if not script_url:
            return None

        return name, file_name, script_url

    files = [os.path.join(DIR, f) for f in os.listdir(DIR) if os.path.isfile(
        os.path.join(DIR, f)) and os.path.getsize(os.path.join(DIR, f)) > 3000]

    metadata = {}
    script_pages = get_script_pages()

    for script_page_url in tqdm(script_pages, desc=SOURCE):
        details = get_script_details(script_page_url)
        if details is None:
            continue

        name, file_name, script_url = details

        metadata[name] = {
            "file_name": file_name,
            "script_url": script_url
        }

        if os.path.join(DIR, file_name + '.txt') in files:
            continue

        text = get_script_from_url(script_url, file_name)
        if text == "" or name == "":
            metadata.pop(name, None)
            continue

        with open(os.path.join(DIR, file_name + '.txt'), 'w', errors="ignore") as out:
            out.write(text)
    
    with open(os.path.join(META_DIR, SOURCE + ".json"), "w") as outfile:
        json.dump(metadata, outfile, indent=4)
