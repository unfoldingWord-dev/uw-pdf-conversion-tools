import re
from bs4 import BeautifulSoup
from collections import OrderedDict

PHRASE_PARTS_TO_IGNORE = ['a', 'am', 'an', 'and', 'as', 'are', 'at', 'be', 'by', 'did', 'do', 'does', 'done', 'for', 'from', 'had', 'has', 'have', 'he', 'her', 'his', 'i', 'in', 'into', 'less', 'let', 'may', 'might', 'more', 'my', 'not', 'is', 'of', 'on', 'one', 'onto', 'our', 'she', 'than', 'the', 'their', 'then', 'they', 'this', 'that', 'those', 'these', 'to', 'was', 'we', 'who', 'whom', 'with', 'will', 'were', 'your', 'you', 'would', 'could', 'should', 'shall', 'can']


def get_title_from_html(html):
    header = get_first_header(html)
    if header:
        return header.text


def get_first_header(html):
    headers = get_headers(html)
    if len(headers):
        return headers[0]


def get_headers(html, header_tag=None):
    if not header_tag:
        header_tag = r'^h\d'
    if isinstance(header_tag, str) and header_tag.startswith('^'):
        header_tag = re.compile(header_tag)
    soup = BeautifulSoup(html, 'html.parser')
    return soup.find_all(header_tag)


def get_phrases_to_highlight(html, header_tag=None):
    phrases = []
    if header_tag:
        headers = get_headers(html, header_tag)
    else:
        headers = get_headers('^h[3-6]')
    for header in headers:
        phrases.append(header.text)
    return phrases


def mark_phrase_in_text(text, phrase, tag=None):
    if not tag:
        tag = '<span class="highlight">'
    tag_name = tag[1:-1].split(' ')[0]
    parts = re.split(r'\s*s…\s*|\s*\.\.\.\s*', phrase)
    processed_text = ''
    to_process_text = text
    for idx, part in enumerate(parts):
        part = part.strip()
        if not part or (idx != len(parts) - 1 and part.lower() in PHRASE_PARTS_TO_IGNORE):
            continue
        if re.findall('<[^>]+>', to_process_text):
            words = [re.escape(word.strip()) for word in re.findall(r'\w+|\W+', part)]
            split_pattern = '(' + r'(\s*|(\s*</*[^>]+>\s*)+)'.join(words) + ')'
        else:
            split_pattern = '(' + re.escape(part) + ')'
        split_pattern += '(?![^<]*>)'  # don't match within HTML tags
        splits = re.split(split_pattern, to_process_text, 1)
        processed_text += splits[0]
        if len(splits) > 1:
            processed_text += f'{tag}{splits[1]}</{tag_name}>'
            if len(splits) > 2:
                to_process_text = splits[-1]
            else:
                to_process_text = ''
        else:
            to_process_text = ''
    if to_process_text:
        processed_text += to_process_text
    if processed_text != text:
        return processed_text


def find_quote_variation_in_text(text, phrase):
    quote_variations = [
        # All curly quotes made straight
        phrase.replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"'),
        # All straight quotes made curly, first single and double pointing right
        phrase.replace("'", '’').replace('’', '‘', 1).replace('"', '”').replace('”', '“', 1),
        # All curly double quotes made straight
        phrase.replace('“', '"').replace('”', '"'),
        # All straight double quotes made curly with first pointing right
        phrase.replace('"', '”').replace('”', '“', 1),
        # All straight single quotes made curly with first pointing right
        phrase.replace("'", '’').replace('’', '‘', 1),
        # All straight single quotes made straight (all point left)
        phrase.replace("'", '’'),
        # All left pointing curly single quotes made straight
        phrase.replace('’', "'"),
        # All right pointing curly single quotes made straight
        phrase.replace('‘', "'")]
    for quote_variation in quote_variations:
        if quote_variation != phrase:
            marked_text = mark_phrase_in_text(text, quote_variation)
            if marked_text:
                return quote_variation


def increment_headers(html, increase_depth=1):
    if html:
        soup = BeautifulSoup(html, 'html.parser')
        for level in range(5, 0, -1):
            new_level = level + increase_depth
            if new_level > 6:
                new_level = 6
            headers = soup.find_all(re.compile(f'^h{level}'))
            for header in headers:
                header.name = f'h{new_level}'
        html = str(soup)
    return html


def decrement_headers(html, minimum_header=2, decrease=1):
    if minimum_header < 2:
        minimum_header = 2
    if html:
        soup = BeautifulSoup(html, 'html.parser')
        for level in range(minimum_header, 6):
            new_level = level - decrease
            if new_level < 1:
                new_level = 1
            headers = soup.find_all(re.compile(rf'^h{level}'))
            for header in headers:
                header.name = f'h{new_level}'
        html = str(soup)
    return html


def make_first_header_section_header(html):
    soup = BeautifulSoup(html, 'html.parser')
    header = soup.find(re.compile(r'^h\d'))
    if header:
        header['class'] = header.get('class', []) + ['section-header']
    return str(soup)
