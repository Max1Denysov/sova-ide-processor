import html
import re

from bs4 import BeautifulSoup

MANAGE_RE = r"^\s*(\$)"


def extract_template_vars(text):
    """
    Extract all template references from templates content.

    :param text:
    :return:
    """
    set_entries = re.findall(r"[\+\(\[]\s*\%([\w.\-_]+)", text, re.MULTILINE)
    func_entries = re.findall(r'\[\s*@(?:set|SetValue)\s*\(\s*"([\w.\-_]+)"',
                              text, re.IGNORECASE | re.MULTILINE)
    return set(set_entries) | set(func_entries)


def extract_content_dicts(template_text):
    """
    Extract dictionary references from template content.

    :param template_text:
    :return:
    """
    return re.findall(
        r"\[[\w<]*dict\(([\w\-_]+)\)[>]*\]",
        template_text,
        flags=re.MULTILINE | re.IGNORECASE
    )


def extract_include_dicts(text):
    """
    Extract include dictionaries in dictionaries.

    :param text:
    :return:
    """
    elems = re.findall(
        r"--include\(([\w\-_]+)\)",
        text,
        flags=re.MULTILINE | re.IGNORECASE
    )
    return [el.lower() for el in elems]


def _process_name(name):
    name = name.replace(" ", "_")
    name = name.replace("'", "")
    return name


def _process_filename(name):
    name = _process_name(name)
    name = name.replace("(", "").replace(")", "")
    return name


def process_dictionary_name(name):
    name = _process_filename(name.lower())
    return name


def transform_template_text(text):
    """
    Transform from database representantion from frontend to text for compiler

    :param text:
    :return:
    """
    text = text.replace("<br>", "\n")
    soup = BeautifulSoup(text, "html.parser")

    for div in soup.find_all("div"):
        continue_prev_line = False
        if re.search(r"^\s+", div.text) and not re.search(MANAGE_RE, div.text):
            continue_prev_line = True

        div.replace_with(("" if continue_prev_line else "\n") + div.text)

    out_text = soup.text.strip()
    out_text2 = html.unescape(out_text)
    return out_text2
