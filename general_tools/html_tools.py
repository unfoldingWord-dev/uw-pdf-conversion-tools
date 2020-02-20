import re
from bs4 import BeautifulSoup, Tag

PHRASE_PARTS_TO_IGNORE = ['a', 'am', 'an', 'and', 'as', 'are', 'at', 'be', 'by', 'did', 'do', 'does', 'done', 'for', 'from', 'had', 'has', 'have', 'i', 'in', 'into', 'less', 'let', 'may', 'might', 'more', 'my', 'not', 'is', 'of', 'on', 'one', 'onto', 'than', 'the', 'their', 'then', 'this', 'that', 'those', 'these', 'to', 'was', 'we', 'who', 'whom', 'with', 'will', 'were', 'your', 'you', 'would', 'could', 'should', 'shall', 'can']


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


def get_strings(wrapper):
    strings = []
    for el in wrapper.contents:
        if type(el) == Tag:
            strings += get_strings(el)
        else:
            strings.append(el)
    return strings


def mark_phrases_in_html(html, phrases, tag='<span class="highlight">', break_on_word=True):
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.text
    for phrase_idx, words in enumerate(phrases):
        phrase = ''
        for word in words:
            phrase += word['text']
        phrase = phrase.strip()

        if not phrase or (phrase_idx < len(phrases) - 1 and phrase.lower() in PHRASE_PARTS_TO_IGNORE):
            continue

        first_word = words[0]['text']
        first_word_occurrence = words[0]['occurrence']

        word_break = r'\b'
        if not break_on_word:
            word_break = ''

        start_indices = [i.start() for i in re.finditer(f'{word_break}{re.escape(first_word)}{word_break}', text)]
        if len(start_indices) < first_word_occurrence:
            return
        phrase_start = start_indices[first_word_occurrence - 1]
        phrase_end = start_indices[first_word_occurrence - 1] + len(phrase)

        if phrase_end > len(text) or phrase != text[phrase_start:phrase_end]:
            return

        strings = get_strings(soup)
        to_process_index = 0
        string = strings.pop(0)
        while (to_process_index + len(string)) <= phrase_start:
            to_process_index += len(string)
            string = strings.pop(0)

        while to_process_index < phrase_end:
            match_start = phrase_start - to_process_index
            match_end = phrase_end - to_process_index
            if match_start < 0:
                match_start = 0
            if match_end > len(string):
                match_end = len(string)

            pre_match_str = string[:match_start]
            pre_match = soup.new_string(pre_match_str)
            string.replace_with(pre_match)

            match_str = string[match_start:match_end]
            match_tag_soup = BeautifulSoup(tag, 'html.parser')
            match_tag = match_tag_soup.find()
            match_tag.string = match_str
            pre_match.insert_after(match_tag)

            if match_end < len(string):
                post_match_str = string[match_end:]
                post_match = soup.new_string(post_match_str)
                match_tag.insert_after(post_match)
                strings.insert(0, post_match)

            to_process_index += match_end
            if to_process_index < phrase_end:
                string = strings.pop(0)
    return str(soup)


def unnest_a_links(html):
    # This cleans up nested <a> links by separating the links and making sure links don't start and end with spaces
    # See https://regex101.com/r/HWO7JO/2 for example usage
    while re.search('<a[^>]*>((?!</a[^>]*>).)*?<a', html):
        html = re.sub(r'<a([^>]*)>(\s*)((?:(?!</*a[^>]*>).)*?)(\s*)<a([^>]*)>(\s*)((?:(?:(?!</*a[^>]*>).)*?|</a>(?:(?!</*a[^>]*>).)*?<a[^>]*>)*?)(\s*)</a>(\s*)((?:(?!</*a[^>]*>).)*?)(\s*)</a>',
                      r'\2<span class="nested-link nested-link-outer"><a\1>\3</a>\4\6<span class="nested-link nested-link-inner"><a\5>\7</a></span>\8\9<a\1>\10</a></span>\11', html, flags=re.MULTILINE)
    return html


def find_quote_variation_in_text(text, phrase, occurrence=1, ignore_small_words=True):
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
            marked_text = mark_phrases_in_html(text, quote_variation, occurrence=occurrence,
                                               ignore_small_words=ignore_small_words)
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


def make_first_header_section_header(html, level=None, no_toc=False):
    soup = BeautifulSoup(html, 'html.parser')
    header = soup.find(re.compile(r'^h\d'))
    classes = ['section-header']
    if no_toc:
        classes.append('no-toc')
    if header:
        header['class'] = header.get('class', []) + classes
        if level:
            header.name = f'h{level}'
    return str(soup)
