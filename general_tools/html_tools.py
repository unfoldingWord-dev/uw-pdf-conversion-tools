import re
from bs4 import BeautifulSoup
from collections import OrderedDict


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


def highlight_text(html, phrase):
    parts = re.split(r'\s*…\s*|\s*\.\.\.\s*', phrase)
    processed_text = ''
    to_process_text = html
    for idx, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
        if '<span' in to_process_text:
            words = re.findall(r'\w+|\W+', part)
            words = [re.escape(word.strip()) for word in words]
            split_pattern = '(' + r'(\s*|(\s*</*span[^>]*>\s*)+)'.join(words) + ')'
        else:
            split_pattern = '(' + re.escape(part) + ')'
        split_pattern += '(?![^<]*>)'  # don't match within HTML tags
        splits = re.split(split_pattern, to_process_text, 1)
        processed_text += splits[0]
        if len(splits) > 1:
            highlight_classes = "highlight"
            if len(parts) > 1:
                highlight_classes += ' split'
            processed_text += f'<span class="{highlight_classes}">{splits[1]}</span>'
            if len(splits) > 2:
                to_process_text = splits[-1]
            else:
                to_process_text = ''
        else:
            to_process_text = ''
    if to_process_text:
        processed_text += to_process_text
    return processed_text


def highlight_text_with_phrases(orig_text, phrases, rc, ignore=None, add_bad_highlight_func=None):
    highlighted_text = orig_text
    phrases.sort(key=len, reverse=True)
    for phrase in phrases:
        new_highlighted_text = highlight_text(highlighted_text, phrase)
        if new_highlighted_text != highlighted_text:
            highlighted_text = new_highlighted_text
        elif not ignore or phrase.lower() not in ignore:
            # This is just to determine the fix for any terms that differ in curly/straight quotes
            bad_highlights = OrderedDict({phrase: None})
            alt_phrase = [
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
            for alt_phrase in alt_phrase:
                if orig_text != highlight_text(orig_text, alt_phrase):
                    bad_highlights[phrase] = alt_phrase
                    break
            if add_bad_highlight_func:
                add_bad_highlight_func(rc, orig_text, bad_highlights)
    return highlighted_text


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
