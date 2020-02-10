#!/usr/bin/env python3
#
#  Copyright (c) 2020 unfoldingWord
#  http://creativecommons.org/licenses/MIT/
#  See LICENSE file for details.
#
#  Contributors:
#  Richard Mahn <rich.mahn@unfoldingword.org>

"""
This script generates the HTML and PDF TN documents
"""
import os
import re
import argparse
import csv
import markdown2
import subprocess
import general_tools.html_tools as html_tools
from glob import glob
from bs4 import BeautifulSoup
from collections import OrderedDict
from pdf_converter import PdfConverter, run_converter
from tx_usfm_tools.singleVerseHtmlRenderer import SingleVerseHtmlRender
from general_tools.bible_books import BOOK_NUMBERS, BOOK_CHAPTER_VERSES
from general_tools.file_utils import read_file, load_json_object, get_latest_version_path, get_child_directories
from general_tools.usfm_utils import unalign_usfm

DEFAULT_ULT_ID = 'ult'
DEFAULT_UST_ID = 'ust'
QUOTES_TO_IGNORE = ['general information:', 'connecting statement:']


class TnPdfConverter(PdfConverter):

    def __init__(self, *args, ult_id=DEFAULT_ULT_ID, ust_id=DEFAULT_UST_ID, **kwargs):
        super().__init__(*args, **kwargs)
        self.ult_id = ult_id
        self.ust_id = ust_id

        self.resources['ult'].resource_name = self.ult_id
        self.resources['ult'].repo_name = f'{self.lang_code}_{self.ult_id}'
        self.resources['ust'].resource_name = self.ust_id
        self.resources['ust'].repo_name = f'{self.lang_code}_{self.ust_id}'
        self.resources['ugnt'].repo_name = 'el-x-koine_ugnt'
        self.resources['uhb'].repo_name = 'hbo_uhb'

        self.book_number = BOOK_NUMBERS[self.project_id]
        self.verse_usfm = OrderedDict()
        self.tw_words_data = OrderedDict()
        self.tn_groups_data = OrderedDict()
        self.tn_book_data = OrderedDict()
        self.tw_rcs = {}
        self.last_ended_with_quote_tag = False
        self.last_ended_with_paragraph_tag = False
        self.open_quote = False
        self.next_follows_quote = False

        if int(self.book_number) < 40:
            self.ol_bible_id = 'uhb'
            self.ol_lang_code = 'hbo'
        else:
            self.ol_bible_id = 'ugnt'
            self.ol_lang_code = 'el-x-koine'

    @property
    def name(self):
        return 'tn'

    @property
    def file_id_project_str(self):
        if self.project_id:
            return f'_{self.book_number.zfill(2)}-{self.project_id.upper()}'
        else:
            return ''

    def process_bibles(self):
        if not self.offline and (self.resources[self.ult_id].new_commits or self.resources[self.ust_id].new_commits or
                                 self.resources['tn'].new_commits or self.resources['tw'].new_commits or
                                 self.resources[self.ol_bible_id].new_commits):
            cmd = f'cd "{self.converters_dir}/tn_resources" && node start.js {self.lang_code} "{self.working_dir}" {self.ult_id} {self.ust_id}'
            self.logger.info(f'Running: {cmd}')
            ret = subprocess.call(cmd, shell=True)
            if ret:
                self.logger.error('Error running tn_resources/processBibles.js. Exiting.')
                exit(1)

    def get_body_html(self):
        self.logger.info('Creating tN for {0}...'.format(self.file_project_and_tag_id))
        self.process_bibles()
        self.populate_tw_words_data()
        self.populate_tn_groups_data()
        self.populate_tn_book_data()
        self.populate_verse_usfm(self.ult_id)
        self.populate_verse_usfm(self.ust_id)
        return self.get_tn_html()

    def pad(self, num):
        if self.project_id == 'psa':
            return str(num).zfill(3)
        else:
            return str(num).zfill(2)

    def get_usfm_from_verse_objects(self, verse_objects):
        usfm = ''
        for idx, obj in enumerate(verse_objects):
            if obj['type'] == 'milestone':
                usfm += self.get_usfm_from_verse_objects(obj['children'])
            elif obj['type'] == 'word':
                if not self.next_follows_quote and obj['text'] != 's':
                    usfm += ' '
                usfm += obj['text']
                self.next_follows_quote = False
            elif obj['type'] == 'text':
                obj['text'] = obj['text'].replace('\n', '').strip()
                if not self.open_quote and len(obj['text']) > 2 and obj['text'][-1] == '"':
                    obj['text'] = f"{obj['text'][:-1]} {obj['text'][-1]}"
                if not self.open_quote and obj['text'] == '."':
                    obj['text'] = '. "'
                if len(obj['text']) and obj['text'][0] == '"' and not self.open_quote and obj['text'] not in ['-', '—']:
                    usfm += ' '
                usfm += obj['text']
                if obj['text'].count('"') == 1:
                    self.open_quote = not self.open_quote
                if self.open_quote and '"' in obj['text'] or obj['text'] in ['-', '—', '(', '[']:
                    self.next_follows_quote = True
            elif obj['type'] == 'quote':
                obj['text'] = obj['text'].replace('\n', '').strip() if 'text' in obj else ''
                if idx == len(verse_objects) - 1 and obj['tag'] == 'q' and len(obj['text']) == 0:
                    self.last_ended_with_quote_tag = True
                else:
                    usfm += f"\n\\{obj['tag']} {obj['text'] if len(obj['text']) > 0 else ''}"
                if obj['text'].count('"') == 1:
                    self.open_quote = not self.open_quote
                if self.open_quote and '"' in obj['text']:
                    self.next_follows_quote = True
            elif obj['type'] == 'section':
                obj['text'] = obj['text'].replace('\n', '').strip() if 'text' in obj else ''
            elif obj['type'] == 'paragraph':
                obj['text'] = obj['text'].replace('\n', '').strip() if 'text' in obj else ''
                if idx == len(verse_objects) - 1 and not obj['text']:
                    self.last_ended_with_paragraph_tag = True
                else:
                    usfm += f"\n\\{obj['tag']}{obj['text']}\n"
            elif obj['type'] == 'footnote':
                obj['text'] = obj['text'].replace('\n', '').strip() if 'text' in obj else ''
                usfm += f' \\{obj["tag"]} {obj["content"]} \\{obj["tag"]}*'
            else:
                self.logger.error("ERROR! Not sure what to do with this:")
                self.logger.error(obj)
                exit(1)
        return usfm

    def populate_verse_usfm(self, bible_id):
        book_data = OrderedDict()
        book_file = os.path.join(self.resources[bible_id].repo_dir, f'{self.book_number}-{self.project_id.upper()}.usfm')
        usfm3 = read_file(book_file)
        usfm2 = unalign_usfm(usfm3)
        chapters = usfm2.split(r'\c ')
        for chapter_usfm in chapters[1:]:
            chapter = re.findall(r'(\d+)', chapter_usfm)[0]
            book_data[chapter] = OrderedDict()
            chapter_usfm = r'\c '+chapter_usfm
            verses = chapter_usfm.split(r'\v ')
            for verse_usfm in verses[1:]:
                from_verse, to_verse = re.findall(r'^(\d+)(?:-(\d+))*', verse_usfm)[0]
                if not to_verse:
                    to_verse = from_verse
                for verse in range(int(from_verse), int(to_verse)+1):
                    verse = str(verse)
                    new_verse_usfm = rf'\v {verse_usfm}'
                    new_verse_html = self.get_verse_html(new_verse_usfm, bible_id, chapter, verse)
                    book_data[chapter][verse] = {
                        'usfm': new_verse_usfm,
                        'html': new_verse_html
                    }
        self.verse_usfm[bible_id] = book_data

    @staticmethod
    def unicode_csv_reader(utf8_data, dialect=csv.excel, **kwargs):
        csv_reader = csv.reader(utf8_data, dialect=dialect, delimiter=str("\t"), quotechar=str('"'), **kwargs)
        for row in csv_reader:
            yield [cell for cell in row]

    def populate_tn_book_data(self):
        book_file = os.path.join(self.main_resource.repo_dir,
                                 f'{self.lang_code}_tn_{self.book_number}-{self.project_id.upper()}.tsv')
        if not os.path.isfile(book_file):
            return
        book_data = OrderedDict()
        reader = self.unicode_csv_reader(open(book_file))
        header = next(reader)
        for row in reader:
            verse_data = {
                'contextId': None,
                f'{self.ult_id}Quote': None,
                f'{self.ust_id}Quote': None
            }
            found = False
            for idx, field in enumerate(header):
                field = field.strip()
                if idx >= len(row):
                    self.logger.error(f'ERROR: {book_file} is malformed')
                    found = False
                    break
                else:
                    found = True
                    verse_data[field] = row[idx]
            if not found:
                break
            chapter = verse_data['Chapter'].lstrip('0')
            verse = verse_data['Verse'].lstrip('0')
            occurrence = int(verse_data['Occurrence'])
            tn_rc_link = f'rc://{self.lang_code}/tn/help/{self.project_id}/{self.pad(chapter)}/{verse.zfill(3)}/{verse_data["ID"]}'
            tn_title = verse_data['GLQuote'] + ' (GLQuote)'
            if verse_data['OrigQuote']:
                context_id = None
                if chapter in self.tn_groups_data and verse in self.tn_groups_data[chapter] and \
                    self.tn_groups_data[chapter][verse]:
                    for c_id in self.tn_groups_data[chapter][verse]:
                        if c_id['quoteString'] == verse_data['OrigQuote'] and c_id['occurrence'] == occurrence:
                            context_id = c_id
                            break
                if not context_id and chapter.isdigit() and verse.isdigit():
                    parts = re.split(r'\s*s…\s*|\s*\.\.\.\s*', verse_data['OrigQuote'])
                    if len(parts) > 1:
                        quote = []
                        for part in parts:
                            quote.append({'word': part})
                    else:
                        quote = verse_data['OrigQuote']
                    context_id = {
                        'reference': {
                            'chapter': int(chapter),
                            'verse': int(verse)
                        },
                        'quote': quote,
                        'occurrence': verse_data['Occurrence']
                    }
                if context_id:
                    context_id['rc'] = tn_rc_link
                    verse_data['contextId'] = context_id
                    verse_data[f'{self.ult_id}Quote'] = self.get_aligned_text(self.ult_id, context_id)
                    verse_data[f'{self.ust_id}Quote'] = self.get_aligned_text(self.ust_id, context_id)
                new_title = ''
                if verse_data[f'{self.ult_id}Quote']:
                    new_title = verse_data[f'{self.ult_id}Quote'] + f' ({self.ult_id.upper()})'
                if verse_data[f'{self.ust_id}Quote']:
                    if new_title:
                        new_title += '; '
                    new_title += verse_data[f'{self.ust_id}Quote'] + f' ({self.ust_id.upper()})'
                if new_title:
                    tn_title = new_title
            tn_rc = self.create_rc(tn_rc_link, title=tn_title)
            verse_data['title'] = tn_title
            verse_data['rc'] = tn_rc
            if chapter not in book_data:
                book_data[chapter] = OrderedDict()
            if verse not in book_data[chapter]:
                book_data[chapter][verse] = []
            book_data[str(chapter)][str(verse)].append(verse_data)
        self.tn_book_data = book_data

    def get_tn_html(self):
        tn_html = f'''
<section id="{self.lang_code}-{self.name}-{self.project_id}" class="{self.name}">
    <article id="{self.lang_code}-{self.name}-{self.project_id}-cover" class="resource-title-page">
        <img src="images/{self.main_resource.logo_file}" class="logo" alt="UTN">
        <h1 class="section-header">{self.title}</h1>
        <h2 class="section-header">{self.project_title}</h2>
    </article>
'''
        if 'front' in self.tn_book_data and 'intro' in self.tn_book_data['front']:
            book_intro = markdown2.markdown(self.tn_book_data['front']['intro'][0]['OccurrenceNote'].replace('<br>', '\n'))
            book_intro_title = html_tools.get_title_from_html(book_intro)
            book_intro = self.fix_tn_links(book_intro, 'intro')
            book_intro = html_tools.make_first_header_section_header(book_intro, level=3)
            # HANDLE FRONT INTRO RC LINKS
            book_intro_rc_link = f'rc://{self.lang_code}/{self.name}/help/{self.project_id}/front/intro'
            book_intro_rc = self.add_rc(book_intro_rc_link, title=book_intro_title)
            book_intro = f'''
    <article id="{book_intro_rc.article_id}">
        {book_intro}
    </article>
'''
            book_intro_rc.set_article(book_intro)
            tn_html += book_intro
        for chapter in BOOK_CHAPTER_VERSES[self.project_id]:
            self.logger.info(f'Chapter {chapter}...')
            chapter_title = f'{self.project_title} {chapter}'
            # HANDLE INTRO RC LINK
            chapter_rc_link = f'rc://{self.lang_code}/{self.name}/help/{self.project_id}/{self.pad(chapter)}'
            chapter_rc = self.add_rc(chapter_rc_link, title=chapter_title)
            tn_html += f'''
    <section id="{chapter_rc.article_id}" class="tn-chapter">
        <h3 class="section-header">{chapter_title}</h3>
'''
            if 'intro' in self.tn_book_data[chapter]:
                self.logger.info('Generating chapter info...')
                chapter_intro = markdown2.markdown(self.tn_book_data[chapter]['intro'][0]['OccurrenceNote'].replace('<br>', "\n"))
                # Remove leading 0 from chapter heading
                chapter_intro = re.sub(r'<h(\d)>([^>]+) 0+([1-9])', r'<h\1>\2 \3', chapter_intro, 1, flags=re.MULTILINE | re.IGNORECASE)
                chapter_intro = html_tools.make_first_header_section_header(chapter_intro, level=4, no_toc=True)
                chapter_intro_title = html_tools.get_title_from_html(chapter_intro)
                chapter_intro = self.fix_tn_links(chapter_intro, chapter)
                # HANDLE INTRO RC LINK
                chapter_intro_rc_link = f'rc://{self.lang_code}/{self.name}/help/{self.project_id}/{self.pad(chapter)}/chapter_intro'
                chapter_intro_rc = self.add_rc(chapter_intro_rc_link, title=chapter_intro_title)
                chapter_intro = f'''
        <article id="{chapter_intro_rc.article_id}">
            {chapter_intro}
        </article>
'''
                chapter_intro_rc.set_article(chapter_intro)
                tn_html += chapter_intro

            for verse in range(1,  int(BOOK_CHAPTER_VERSES[self.project_id][chapter]) + 1):
                verse = str(verse)
                self.logger.info(f'Generating verse {chapter}:{verse}...')
                tn_html += self.get_tn_article(chapter, verse)
            tn_html += '''
    </section>
'''
        tn_html += '''
</section>
'''
        self.logger.info('Done generating tN HTML.')
        return tn_html

    def get_tn_article(self, chapter, verse):
        tn_title = f'{self.project_title} {chapter}:{verse}'
        tn_rc_link = f'rc://{self.lang_code}/{self.name}/help/{self.project_id}/{self.pad(chapter)}/{verse.zfill(3)}'
        tn_rc = self.add_rc(tn_rc_link, title=tn_title)
        tn_article = f'''
                <article id="{tn_rc.article_id}">
                    <h3 class="section-header no-toc">{tn_title}</h3>
                    <div class="tn-notes">
                            <div class="col1">
                                {self.get_scripture(chapter, verse)}
                            </div>
                            <div class="col2">
                                {self.get_tn_article_text(chapter, verse)}
                                {self.get_tw_html_list(self.ult_id, chapter, verse)}
                                {self.get_tw_html_list(self.ust_id, chapter, verse)}
                            </div>
                    </div>
                </article>
'''
        tn_rc.set_article(tn_article)
        return tn_article

    def get_tw_html_list(self, resource_id, chapter, verse):
        words = self.get_words(resource_id, chapter, verse)
        if not words:
            return ''
        links = OrderedDict()
        for word_idx, word in enumerate(words):
            word_count = word_idx + 1
            phrase = word['text']
            tw_rc = word['contextId']['rc']
            occurrence = word['contextId']['occurrence']
            occurrence_text = ''
            if occurrence > 1:
                occurrence_text = f' ({occurrence})'
            links[phrase] = f'<a href="{tw_rc}" class="tw-phrase tw-phrase-{word_count}">{phrase}</a>{occurrence_text}'
        tw_html = f'''
                <h3>{self.resources['tw'].simple_title} - {resource_id.upper()}</h3>
                <ul class="tw-list">
                    <li>{'</li><li>'.join(links.values())}</li>
                </ul>
'''
        return tw_html

    def get_scripture(self, chapter, verse, rc=None):
        ult_with_tw_words = self.get_scripture_with_tw_words(self.ult_id, chapter, verse, rc)
        ult_with_tw_words = self.get_scripture_with_tn_quotes(self.ult_id, chapter, verse, rc, ult_with_tw_words)
        ust_with_tw_words = self.get_scripture_with_tw_words(self.ust_id, chapter, verse, rc)
        ust_with_tw_words = self.get_scripture_with_tn_quotes(self.ust_id, chapter, verse, rc, ust_with_tw_words)

        scripture = f'''
            <h3 class="bible-resource-title">{self.ult_id.upper()}</h3>
            <div class="bible-text">{ult_with_tw_words}</div>
            <h3 class="bible-resource-title">{self.ust_id.upper()}</h3>
            <div class="bible-text">{ust_with_tw_words}</div>
'''
        return scripture

    def get_tn_article_text(self, chapter, verse):
        verse_notes = ''
        if verse in self.tn_book_data[chapter]:
            tn_notes = self.get_tn_notes(chapter, verse)
            for tn_note in tn_notes:
                note = markdown2.markdown(tn_note['OccurrenceNote'].replace('<br>', "\n"))
                note = re.sub(r'</*p[^>]*>', '', note, flags=re.IGNORECASE | re.MULTILINE)
                verse_notes += f'''
        <div id="{tn_note['rc'].article_id}" class="verse-note">
            <h3 class="verse-note-title">{tn_note['title']}</h3>
            <div class="verse-note-text">
                {note}
            </div>
        </div>
'''
        else:
            verse_notes += f'''
        <div class="no-notes">
            ({self.translate('no_notes_for_this_verse')})
        </div>
'''
        verse_notes = self.fix_tn_links(verse_notes, chapter)
        return verse_notes

    def populate_tw_words_data(self):
        tw_path = os.path.join(self.working_dir, 'resources', self.ol_lang_code, 'translationHelps/translationWords')
        if not tw_path:
            self.logger.error(f'{tw_path} not found!')
            exit(1)
        tw_version_path = get_latest_version_path(tw_path)
        if not tw_version_path:
            self.logger.error(f'No versions found in {tw_path}!')
            exit(1)

        groups = get_child_directories(tw_version_path)
        words_data = OrderedDict()
        for group in groups:
            files_path = os.path.join(tw_version_path, f'{group}/groups/{self.project_id}', '*.json')
            files = glob(files_path)
            for file in files:
                base = os.path.splitext(os.path.basename(file))[0]
                tw_rc_link = f'rc://{self.lang_code}/tw/dict/bible/{group}/{base}'
                occurrences = load_json_object(file)
                for occurrence in occurrences:
                    context_id = occurrence['contextId']
                    chapter = str(context_id['reference']['chapter'])
                    verse = str(context_id['reference']['verse'])
                    context_id['rc'] = tw_rc_link
                    if chapter not in words_data:
                        words_data[chapter] = OrderedDict()
                    if verse not in words_data[chapter]:
                        words_data[chapter][verse] = []
                    words_data[chapter][verse].append(context_id)
        self.tw_words_data = words_data

    def populate_tn_groups_data(self):
        tn_resource_path = os.path.join(self.working_dir, 'resources', self.lang_code, 'translationHelps', 'translationNotes')
        if not tn_resource_path:
            self.logger.error(f'{tn_resource_path} not found!')
            exit(1)
        tn_version_path = get_latest_version_path(tn_resource_path)
        if not tn_version_path:
            self.logger.error(f'Version not found in {tn_resource_path}!')
            exit(1)

        groups = get_child_directories(tn_version_path)
        groups_data = OrderedDict()
        for group in groups:
            files_path = os.path.join(tn_version_path, f'{group}/groups/{self.project_id}', '*.json')
            files = glob(files_path)
            for file in files:
                base = os.path.splitext(os.path.basename(file))[0]
                occurrences = load_json_object(file)
                for occurrence in occurrences:
                    context_id = occurrence['contextId']
                    chapter = str(context_id['reference']['chapter'])
                    verse = str(context_id['reference']['verse'])
                    tn_rc_link = f'rc://{self.lang_code}/tn/help/{self.project_id}/{self.pad(chapter)}/{verse.zfill(3)}/{group}/{base}'
                    context_id['rc'] = tn_rc_link
                    if chapter not in groups_data:
                        groups_data[chapter] = OrderedDict()
                    if verse not in groups_data[chapter]:
                        groups_data[chapter][verse] = []
                    groups_data[chapter][verse].append(context_id)
        self.tn_groups_data = groups_data

    def get_plain_scripture(self, bible_id, chapter, verse):
        data = self.verse_usfm[bible_id][chapter][verse]
        footnotes_split = re.compile('<div class="footnotes">', flags=re.IGNORECASE | re.MULTILINE)
        verses_and_footnotes = re.split(footnotes_split, data['html'], maxsplit=1)
        scripture = verses_and_footnotes[0]
        footnotes = ''
        if len(verses_and_footnotes) == 2:
            footnote = f'<div class="footnotes">{verses_and_footnotes[1]}'
            if footnotes:
                footnote = footnote.replace('<hr class="footnotes-hr"/>', '')
            footnotes += footnote
        html = ''
        if scripture:
            scripture = re.sub(r'\s*<span class="v-num"', '</div><div class="verse"><span class="v-num"', scripture, flags=re.IGNORECASE | re.MULTILINE)
            scripture = re.sub(r'^</div>', '', scripture)
            if scripture and '<div class="verse">' in scripture:
                scripture += '</div>'
            html = scripture + footnotes
            html = re.sub(r'\s*\n\s*', ' ', html, flags=re.IGNORECASE | re.MULTILINE)
            html = re.sub(r'\s*</*p[^>]*>\s*', ' ', html, flags=re.IGNORECASE | re.MULTILINE)
            html = html.strip()
            html = re.sub('id="(ref-)*fn-', rf'id="{bible_id}-\1fn-', html,
                          flags=re.IGNORECASE | re.MULTILINE)
            html = re.sub('href="#(ref-)*fn-', rf'href="#{bible_id}-\1fn-', html,
                          flags=re.IGNORECASE | re.MULTILINE)
        return html

    def get_scripture_with_tw_words(self, bible_id, chapter, verse, rc=None, ignore_small_words=True):
        scripture = self.get_plain_scripture(bible_id, chapter, verse)
        footnotes_split = re.compile('<div class="footnotes">', flags=re.IGNORECASE | re.MULTILINE)
        verses_and_footnotes = re.split(footnotes_split, scripture, maxsplit=1)
        scripture = verses_and_footnotes[0]
        footnote = ''
        if len(verses_and_footnotes) == 2:
            footnote = f'<div class="footnotes">{verses_and_footnotes[1]}'
        occurrences = {}
        orig_scripture = scripture
        words = self.get_words(bible_id, chapter, verse)
        for word_idx, word in enumerate(words):
            word_count = word_idx + 1
            phrase = word['text']
            tw_rc = word['contextId']['rc']
            occurrence = word['contextId']['occurrence']
            if phrase in occurrences and occurrences[phrase] >= occurrence:
                occurrence = occurrences[phrase] + 1
            occurrences[phrase] = occurrence
            split = ''
            if '…' in phrase or '...' in phrase:
                split = ' split'
            tag = f'<a href="{tw_rc}" class="tw-phrase tw-phrase-{word_count}{split}">'
            marked_verse_html = html_tools.mark_phrase_in_html(scripture, phrase,
                                                               occurrence=occurrence,
                                                               tag=tag,
                                                               ignore_small_words=ignore_small_words)
            # if not marked_verse_html:
            #     marked_verse_html = html_tools.mark_phrase_in_html(verse_html, phrase,
            #                                                        occurrence=occurrence,
            #                                                        tag=tag,
            #                                                        ignore_small_words=ignore_small_words,
            #                                                        break_on_word=False)
            if not marked_verse_html:
                fix = html_tools.find_quote_variation_in_text(orig_scripture, phrase,
                                                              occurrence=occurrence,
                                                              ignore_small_words=ignore_small_words)
                if not fix and occurrence > 1:
                    marked_verse_html = html_tools.mark_phrase_in_html(scripture, phrase,
                                                                       occurrence=1,
                                                                       ignore_small_words=ignore_small_words)
                    if marked_verse_html:
                        fix = f'(occurrence = {occurrence}, only occurrence 1 is found)'
                if rc:
                    self.add_bad_highlight(rc, orig_scripture, tw_rc, word['text'], fix)
            else:
                scripture = marked_verse_html
        scripture += footnote
        return scripture

    def get_verse_objects(self, bible_id, chapter, verse):
        bible_path = os.path.join(self.working_dir, 'resources', self.lang_code, 'bibles', bible_id)
        if not bible_path:
            self.logger.error(f'{bible_path} not found!')
            exit(1)
        bible_version_path = get_latest_version_path(bible_path)
        if not bible_version_path:
            self.logger.error(f'No versions found in {bible_path}!')
            exit(1)

        chapter_json_path = f'{bible_version_path}/{self.project_id}/{chapter}.json'
        data = load_json_object(chapter_json_path)
        if verse in data:
            return data[verse]['verseObjects']
        else:
            return []

    def get_words(self, bible_id, chapter, verse):
        words = []
        if chapter in self.tw_words_data and verse in self.tw_words_data[chapter]:
            context_ids = self.tw_words_data[chapter][verse]
            for context_id in context_ids:
                aligned_text = self.get_aligned_text(bible_id, context_id)
                if aligned_text:
                    words.append({'text': aligned_text, 'contextId': context_id})
        return words

    def get_scripture_with_tn_quotes(self, bible_id, chapter, verse, rc, scripture, ignore_small_words=False):
        if not scripture:
            scripture = self.get_plain_scripture(bible_id, chapter, verse)
        footnotes_split = re.compile('<div class="footnotes">', flags=re.IGNORECASE | re.MULTILINE)
        verses_and_footnotes = re.split(footnotes_split, scripture, maxsplit=1)
        scripture = verses_and_footnotes[0]
        footnote = ''
        if len(verses_and_footnotes) == 2:
            footnote = f'<div class="footnotes">{verses_and_footnotes[1]}'
        tn_notes = self.get_tn_notes(chapter, verse)
        orig_scripture = scripture
        for tn_note_idx, tn_note in enumerate(tn_notes):
            if tn_note[f'{bible_id}Quote']:
                phrase = tn_note[f'{bible_id}Quote']
            else:
                phrase = tn_note['GLQuote']
            split = ''
            if '…' in phrase or '...' in phrase:
                split = ' split'
            tag = f'<span class="highlight tn-phrase tn-phrase-{tn_note_idx+1}{split}">'
            marked_verse_html = html_tools.mark_phrase_in_html(scripture, phrase, tag=tag, ignore_small_words=ignore_small_words)
            if not marked_verse_html:
                fix = None
                if phrase.lower() not in QUOTES_TO_IGNORE:
                    fix = html_tools.find_quote_variation_in_text(orig_scripture, phrase)
                if not fix and tn_note[f'{bible_id}Quote'] and tn_note['GLQuote']:
                    marked_with_gl_quote = html_tools.mark_phrase_in_html(scripture, tn_note['GLQuote'])
                    if marked_with_gl_quote:
                        fix = tn_note['GLQuote']
                self.add_bad_highlight(rc, orig_scripture, tn_note['rc'], tn_note['GLQuote'], fix)
            else:
                scripture = marked_verse_html
        scripture += footnote
        return scripture

    def get_tn_notes(self, chapter, verse):
        notes = []
        if chapter in self.tn_book_data and verse in self.tn_book_data[chapter]:
            for data in self.tn_book_data[chapter][verse]:
                notes.append(data)
        return notes

    @staticmethod
    def find_target_from_combination(verse_objects, quote, occurrence):
        ol_words = []
        word_list = []
        for verse_object in verse_objects:
            if 'content' in verse_object and 'type' in verse_object and verse_object['type'] == 'milestone':
                ol_words.append(verse_object['content'])
                target_words = []
                for child in verse_object['children']:
                    if child['type'] == 'word':
                        target_words.append(child['text'])
                target = ' '.join(target_words)
                found = False
                for idx, word in enumerate(word_list):
                    if word['ol'] == verse_object['content'] and 'occurrence' in verse_object and \
                            word['occurrence'] == verse_object['occurrence']:
                        word_list[idx]['target'] += ' .' \
                                                    '.. ' + target
                        found = True
                if not found:
                    word_list.append({'ol': verse_object['content'], 'target': target, 'occurrence': verse_object['occurrence']})
        combinations = []
        occurrences = {}
        for i in range(0, len(word_list)):
            ol = word_list[i]['ol']
            target = word_list[i]['target']
            for j in range(i, len(word_list)):
                if i != j:
                    ol += ' '+word_list[j]['ol']
                    target += ' '+word_list[j]['target']
                if ol not in occurrences:
                    occurrences[ol] = 0
                occurrences[ol] += 1
                combinations.append({'ol': ol, 'target': target, 'occurrence': occurrences[ol]})
        for combination in combinations:
            if combination['ol'] == quote and combination['occurrence'] == occurrence:
                return combination['target']
        return None

    def find_target_from_split(self, verse_objects, quote, occurrence, is_match=False):
        words_to_match = []
        if isinstance(quote, list):
            for q in quote:
                words_to_match.append(q['word'])
        else:
            words_to_match = quote.split(' ')
        separator = ' '
        needs_ellipsis = False
        text = ''
        for index, verse_object in enumerate(verse_objects):
            last_match = False
            if 'type' in verse_object and (verse_object['type'] == 'milestone' or verse_object['type'] == 'word'):
                if ((('content' in verse_object and verse_object['content'] in words_to_match) or
                     ('lemma' in verse_object and verse_object['lemma'] in words_to_match)) and verse_object['occurrence'] == occurrence) or is_match:
                    last_match = True
                    if needs_ellipsis:
                        separator += '... '
                        needs_ellipsis = False
                    if text:
                        text += separator
                    separator = ' '
                    if 'text' in verse_object and verse_object['text']:
                        text += verse_object['text']
                    if 'children' in verse_object and verse_object['children']:
                        text += self.find_target_from_split(verse_object['children'], quote, occurrence, True)
                elif 'children' in verse_object and verse_object['children']:
                    child_text = self.find_target_from_split(verse_object['children'], quote, occurrence, is_match)
                    if child_text:
                        last_match = True
                        if needs_ellipsis:
                            separator += '... '
                            needs_ellipsis = False
                        text += (separator if text else '') + child_text
                        separator = ' '
                    elif text:
                        needs_ellipsis = True
            if last_match and (index+1) in verse_objects and verse_objects[index + 1]['type'] == "text" and text:
                if separator == ' ':
                    separator = ''
                separator += verse_objects[index + 1]['text']
        return text

    def get_aligned_text(self, bible_id, context_id):
        if not context_id or 'quote' not in context_id or not context_id['quote'] or 'reference' not in context_id or \
                'chapter' not in context_id['reference'] or 'verse' not in context_id['reference']:
            return None
        chapter = str(context_id['reference']['chapter'])
        verse = str(context_id['reference']['verse'])
        verse_objects = self.get_verse_objects(bible_id, chapter, verse)
        if not verse_objects:
            return None
        quote = context_id['quote']
        occurrence = int(context_id['occurrence'])
        text = self.find_target_from_combination(verse_objects, quote, occurrence)
        if not text:
            text = self.find_target_from_split(verse_objects, quote, occurrence)
        if not text:
            title = f'{self.project_title} {chapter}:{verse}'
            aligned_text_rc_link = f'rc://{self.lang_code}/{bible_id}/bible/{self.project_id}/{self.pad(chapter)}/{str(verse).zfill(3)}'
            aligned_text_rc = self.create_rc(aligned_text_rc_link, title=title)
            if int(self.book_number) > 40 or self.project_id.lower() == 'rut' or self.project_id.lower() == 'jon':
                self.add_bad_link(aligned_text_rc, context_id['rc'], 'Bad OL Text')
                self.logger.error(f'{self.lang_code.upper()} {bible_id.upper()} QUOTE NOT FOUND FOR OL QUOTE `{quote}` (occurrence: {occurrence}) IN `{bible_id.upper()} {title}`')
        return text

    def fix_tn_links(self, html, chapter):
        def replace_link(match):
            before_href = match.group(1)
            link = match.group(2)
            after_href = match.group(3)
            linked_text = match.group(4)
            new_link = link
            if link.startswith('../../'):
                # link to another book, which we don't link to so link removed
                return linked_text
            elif link.startswith('../'):
                # links to another verse in another chapter
                link = os.path.splitext(link)[0]
                parts = link.split('/')
                if len(parts) == 3:
                    # should have two numbers, the chapter and the verse
                    c = parts[1]
                    v = parts[2]
                    new_link = f'rc://{self.lang_code}/{self.name}/help/{self.project_id}/{self.pad(c)}/{v.zfill(3)}'
                if len(parts) == 2:
                    # shouldn't be here, but just in case, assume link to the first verse of the given chapter
                    c = parts[1]
                    new_link = f'rc://{self.lang_code}/{self.name}/help/{self.project_id}/{self.pad(c)}/001'
            elif link.startswith('./'):
                # link to another verse in the same chapter
                link = os.path.splitext(link)[0]
                parts = link.split('/')
                v = parts[1]
                new_link = f'rc://{self.lang_code}/{self.name}/help/{self.project_id}/{self.pad(chapter)}/{v.zfill(3)}'
            return f'<a{before_href}href="{new_link}"{after_href}>{linked_text}</a>'
        regex = re.compile(r'<a([^>]+)href="(\.[^"]+)"([^>]*)>(.*?)</a>')
        html = regex.sub(replace_link, html)
        return html

    def get_verse_html(self, usfm, resource_id, chapter, verse):
        usfm = rf'''\id {self.project_id.upper()}
\ide UTF-8
\h {self.project_title}
\mt {self.project_title}

\c {chapter}
{usfm}'''
        html, warnings = SingleVerseHtmlRender(self.project_id.upper(), usfm).render()
        soup = BeautifulSoup(html, 'html.parser')
        header = soup.find('h1')
        if header:
            header.decompose()
        chapter_header = soup.find('h2')
        if chapter_header:
            chapter_header.decompose()
        for span in soup.find_all('span', {'class': 'v-num'}):
            bible_rc_link = f'rc://{self.lang_code}/{resource_id}/bible/{self.project_id}/{self.pad(chapter)}/{verse.zfill(3)}'
            bible_rc = self.create_rc(bible_rc_link)
            span['id'] = bible_rc.article_id
        html = ''.join(['%s' % x for x in soup.body.contents]).strip()
        return html

    def get_go_back_to_html(self, source_rc):
        if source_rc.linking_level == 0:
            return ''
        go_back_tos = []
        book_started = False
        for rc_link in source_rc.references:
            if rc_link in self.rcs:
                rc = self.rcs[rc_link]
                chapter = rc.chapter
                verse = rc.verse
                if chapter == 'front':
                    text = rc.title
                elif verse == 'intro':
                    text = rc.title
                    book_started = True
                else:
                    if book_started:
                        text = rc.title.split(' ')[-1]
                    else:
                        text = rc.title
                    book_started = True
                go_back_tos.append('<a href="#{0}">{1}</a>'.format(rc.article_id, text))
        go_back_to_html = ''
        if len(go_back_tos):
            go_back_tos_string = '; '.join(go_back_tos)
            go_back_to_html = f'''
    <div class="go-back-to">
        (<strong>{self.translate('go_back_to')}:</strong> {go_back_tos_string})
    </div>
'''
        return go_back_to_html


def main(tn_class, resource_names=None):
    if not resource_names:
        resource_names = ['tn', 'ult', 'ust', 'ta', 'tw', 'ugnt', 'uhb']
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--ust-id', dest='ust_id', default=DEFAULT_UST_ID, required=False, help="UST ID")
    parser.add_argument('--ult-id', dest='ult_id', default=DEFAULT_ULT_ID, required=False, help="ULT ID")
    run_converter(resource_names, tn_class, all_project_ids=BOOK_NUMBERS.keys(), parser=parser)


if __name__ == '__main__':
    main(TnPdfConverter)
