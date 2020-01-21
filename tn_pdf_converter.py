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
from subprocess import check_output, STDOUT, CalledProcessError
from glob import glob
from bs4 import BeautifulSoup
from pdf_converter import PdfConverter, run_converter
from usfm_tools.transform import UsfmTransform
from general_tools.bible_books import BOOK_NUMBERS, BOOK_CHAPTER_VERSES
from general_tools.file_utils import write_file, read_file, load_json_object
from general_tools.usfm_utils import usfm3_to_usfm2
from resource import Resource

DEFAULT_ULT_ID = 'ult'
DEFAULT_UST_ID = 'ust'
VERSIFICATION_GITHUB_URL = 'https://git.door43.org/Door43-Catalog/versification.git'
QUOTES_TO_IGNORE = ['general information:', 'connecting statement:']


class TnPdfConverter(PdfConverter):

    def __init__(self, *args, ult_id=DEFAULT_ULT_ID, ust_id=DEFAULT_UST_ID, **kwargs):
        super().__init__(*args, **kwargs)
        self.ult_id = ult_id
        self.ust_id = ust_id
        
        self.ult_package_dir = None
        self.ugnt_package_dir = None
        self.ugnt_tw_dir = None
        self.uhb_package_dir = None
        self.uhb_tw_dir = None
        
        self.resources['ult'].resource_name = self.ult_id
        self.resources['ult'].repo_name = f'{self.lang_code}_{self.ult_id}'
        self.resources['ust'].resource_name = self.ust_id
        self.resources['ust'].repo_name = f'{self.lang_code}_{self.ust_id}'
        self.resources['versification'] = Resource('versification', 'versification', url=VERSIFICATION_GITHUB_URL)
        self.resources['ugnt'].repo_name = 'el-x-koine_ugnt'
        self.resources['uhb'].repo_name = 'hbo_uhb'

        self.book_number = BOOK_NUMBERS[self.project_id]
        self.chapters_and_verses = {}
        self.verse_usfm = {}
        self.chunks_text = {}
        self.tn_book_data = {}
        self.tw_words_data = {}
        self.tw_rcs = {}
        self.last_ended_with_quote_tag = False
        self.last_ended_with_paragraph_tag = False
        self.open_quote = False
        self.next_follows_quote = False
        self.verse_to_chunk = {}

    @property
    def name(self):
        return 'tn'

    @property
    def file_id_project_str(self):
        if self.project_id:
            return f'_{self.book_number.zfill(2)}-{self.project_id.upper()}'
        else:
            return ''
        
    def setup_dirs(self):
        super().setup_dirs()
        self.ult_package_dir = os.path.join(self.working_dir, self.resources['ult'].repo_name + '_master_package')
        self.ugnt_package_dir = os.path.join(self.working_dir, self.resources['ugnt'].repo_name + '_master_package')
        self.ugnt_tw_dir = os.path.join(self.working_dir, self.resources['ugnt'].repo_name + '_master_package' + '_tw_group_data')
        self.uhb_package_dir = os.path.join(self.working_dir, self.resources['uhb'].repo_name + '_master_package')
        self.uhb_tw_dir = os.path.join(self.working_dir, self.resources['uhb'].repo_name + '_master_package' + '_tw_group_data')

    def setup_resources(self):
        super().setup_resources()
        if True or not os.path.exists(self.ult_package_dir) or \
                not os.path.exists(self.ugnt_package_dir) or not os.path.exists(self.ugnt_tw_dir) or \
                not os.path.exists(self.uhb_package_dir) or not os.path.exists(self.uhb_tw_dir):
            cmd = f'cd "{self.converters_dir}/tn_resources" && node processBibles.js {self.lang_code} "{self.working_dir}333" {self.ult_id} {self.ust_id}'
            check_output(cmd, stderr=STDOUT, shell=True)

    def get_body_html(self):
        self.logger.info('Creating tN for {0}...'.format(self.file_project_and_tag_id))
        self.populate_tn_book_data()
        self.populate_tw_words_data()
        self.populate_chapters_and_verses()
        self.populate_verse_usfm()
        self.populate_chunks_text()
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

    def populate_chunks_text(self):
        save_dir = os.path.join(self.output_dir, 'chunks_text')
        save_file = os.path.join(save_dir, '{0}.json'.format(self.file_project_and_tag_id))
        if not self.regenerate and os.path.isfile(save_file):
            self.chunks_text = load_json_object(save_file)
            return

        chunks_text = {}
        for chapter_data in self.chapters_and_verses:
            chapter = chapter_data['chapter']
            chunks_text[str(chapter)] = {}
            for idx, first_verse in enumerate(chapter_data['first_verses']):
                if len(chapter_data['first_verses']) > idx+1:
                    last_verse = chapter_data['first_verses'][idx+1] - 1
                else:
                    last_verse = int(BOOK_CHAPTER_VERSES[self.project_id][str(chapter)])
                chunks_text[str(chapter)][str(first_verse)] = {
                    'first_verse': first_verse,
                    'last_verse': last_verse
                }
                for resource in [self.ult_id, self.ust_id]:
                    verses_in_chunk = []
                    for verse in range(first_verse, last_verse+1):
                        if resource not in self.verse_usfm:
                            self.logger.error('{0} not in verse_usfm!!!'.format(resource))
                            self.logger.error(self.verse_usfm)
                            exit(1)
                        if chapter not in self.verse_usfm[resource]:
                            self.logger.error('Chapter {0} not in {1}!!!'.format(chapter, resource))
                            exit(1)
                        if verse not in self.verse_usfm[resource][chapter]:
                            self.logger.error('{0}:{1} not in {2}!!!'.format(chapter, verse, resource))
                            if len(verses_in_chunk) or resource != self.ult_id:
                                self.verse_usfm[resource][chapter][verse] = ''
                            else:
                                exit(1)
                        verses_in_chunk.append(self.verse_usfm[resource][chapter][verse])
                    chunk_usfm = '\n'.join(verses_in_chunk)
                    if resource not in chunks_text[str(chapter)][str(first_verse)]:
                        chunks_text[str(chapter)][str(first_verse)][resource] = {}
                    chunks_text[str(chapter)][str(first_verse)][resource] = {
                        'usfm': chunk_usfm,
                        'html': self.get_chunk_html(chunk_usfm, resource, chapter, first_verse)
                    }
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            write_file(save_file, chunks_text)
        self.chunks_text = chunks_text

    def populate_verse_usfm(self):
        self.populate_verse_usfm_ult()
        self.populate_verse_usfm_ust()

    def populate_verse_usfm_ust(self):
        book_data = {}
        book_file = os.path.join(self.resources['ust'].repo_dir, f'{self.book_number}-{self.project_id.upper()}.usfm')
        usfm3 = read_file(book_file)
        usfm2 = usfm3_to_usfm2(usfm3)
        chapters = usfm2.split(r'\c ')
        for chapter_usfm in chapters[1:]:
            chapter = int(re.findall(r'(\d+)', chapter_usfm)[0])
            book_data[chapter] = {}
            chapter_usfm = r'\c '+chapter_usfm
            verses = chapter_usfm.split(r'\v ')
            for verse_usfm in verses[1:]:
                verse = int(re.findall(r'(\d+)', verse_usfm)[0])
                verse_usfm = r'\v '+verse_usfm
                if re.match(r'^\\v \d+\s*$', verse_usfm, flags=re.MULTILINE):
                    verse_usfm = ''
                book_data[chapter][verse] = verse_usfm
        self.verse_usfm[self.ust_id] = book_data

    def populate_verse_usfm_ult(self):
        book_data = {}
        book_file = os.path.join(self.resources['ult'].repo_dir, f'{self.book_number}-{self.project_id.upper()}.usfm')
        usfm3 = read_file(book_file)
        usfm2 = usfm3_to_usfm2(usfm3)
        chapters = usfm2.split(r'\c ')
        for chapter_usfm in chapters[1:]:
            chapter = int(re.findall(r'(\d+)', chapter_usfm)[0])
            book_data[chapter] = {}
            chapter_usfm = r'\c '+chapter_usfm
            verses = chapter_usfm.split(r'\v ')
            for verse_usfm in verses[1:]:
                verse = int(re.findall(r'(\d+)', verse_usfm)[0])
                verse_usfm = r'\v '+verse_usfm
                if re.match(r'^\\v \d+\s*$', verse_usfm, flags=re.MULTILINE):
                    verse_usfm = ''
                book_data[chapter][verse] = verse_usfm
        self.verse_usfm[self.ult_id] = book_data

    def populate_chapters_and_verses(self):
        versification_file = os.path.join(self.resources['versification'].repo_dir, 'bible', 'ufw', 'chunks',
                                          f'{self.project_id}.json')
        self.chapters_and_verses = {}
        if os.path.isfile(versification_file):
            self.chapters_and_verses = load_json_object(versification_file)

    @staticmethod
    def unicode_csv_reader(utf8_data, dialect=csv.excel, **kwargs):
        csv_reader = csv.reader(utf8_data, dialect=dialect, delimiter=str("\t"), quotechar=str('"'), **kwargs)
        for row in csv_reader:
            yield [cell for cell in row]

    def populate_tn_book_data(self):
        book_file = os.path.join(self.main_resource.repo_dir,
                                 f'{self.lang_code}_tn_{self.book_number}-{self.project_id.upper()}.tsv')
        self.tn_book_data = {}
        if not os.path.isfile(book_file):
            return
        book_data = {}
        reader = self.unicode_csv_reader(open(book_file))
        header = next(reader)
        for row in reader:
            data = {}
            found = False
            for idx, field in enumerate(header):
                field = field.strip()
                if idx >= len(row):
                    self.logger.error(f'ERROR: {book_file} is malformed')
                    found = False
                    break
                else:
                    found = True
                    data[field] = row[idx]
            if not found:
                break
            chapter = data['Chapter'].lstrip('0')
            verse = data['Verse'].lstrip('0')
            if chapter not in book_data:
                book_data[chapter] = {}
            if verse not in book_data[chapter]:
                book_data[chapter][verse] = []
            book_data[str(chapter)][str(verse)].append(data)
        self.tn_book_data = book_data

    def get_tn_html(self):
        tn_html = f'''
<section id="tn-{self.project_id}">
<div class="resource-title-page">
    <img src="images/{self.main_resource.logo_file}" class="logo" alt="UTN">
    <h1 class="section-header">{self.title}</h1>
    <h2>{self.project_title}</h2>
</div>
'''
        if 'front' in self.tn_book_data and 'intro' in self.tn_book_data['front']:
            intro = markdown2.markdown(self.tn_book_data['front']['intro'][0]['OccurrenceNote'].replace('<br>', '\n'))
            intro_title = html_tools.get_title_from_html(intro)
            intro = self.fix_tn_links(intro, 'intro')
            intro = html_tools.increment_headers(intro)
            intro = html_tools.decrement_headers(intro, 4)  # bring headers of 3 or more down 1
            intro = re.sub(r'<h(\d+)>', r'<h\1 class="section-header">', intro, 1, flags=re.IGNORECASE | re.MULTILINE)
            # HANDLE FRONT INTRO RC LINKS
            intro_rc_link = f'rc://{self.lang_code}/tn/help/{self.project_id}/front/intro'
            intro_rc = self.add_rc(intro_rc_link, title=intro_title)
            self.verse_to_chunk['front'] = {'intro': intro_title}
            intro += f'''
<article id="{intro_rc.article_id}">
    {intro}
</article>
'''
            intro_rc.set_article(intro)
            tn_html += intro
        for chapter_verses in self.chapters_and_verses:
            chapter = str(chapter_verses['chapter'])
            self.verse_to_chunk[self.pad(chapter)] = {}
            self.logger.info(f'Chapter {chapter}...')
            if 'intro' in self.tn_book_data[chapter]:
                self.logger.info('Generating chapter info...')
                intro = markdown2.markdown(self.tn_book_data[chapter]['intro'][0]['OccurrenceNote'].replace('<br>', "\n"))
                intro = re.sub(r'<h(\d)>([^>]+) 0+([1-9])', r'<h\1>\2 \3', intro, 1, flags=re.MULTILINE | re.IGNORECASE)
                intro_title = html_tools.get_title_from_html(intro)
                intro = self.fix_tn_links(intro, chapter)
                intro = html_tools.increment_headers(intro)
                intro = html_tools.decrement_headers(intro, 5, 2)  # bring headers of 5 or more down 2
                intro = re.sub(r'<h(\d+)>', r'<h\1 class="section-header">', intro, 1, flags=re.IGNORECASE | re.MULTILINE)
                # HANDLE INTRO RC LINK
                intro_rc_link = f'rc://{self.lang_code}/tn/help/{self.project_id}/{self.pad(chapter)}/intro'
                intro_rc = self.add_rc(intro_rc_link, title=intro_title)
                self.verse_to_chunk[self.pad(chapter)]['intro'] = intro_title
                intro = f'''
<article id="{intro_rc.article_id}">
    {intro}
</article>
'''
                intro_rc.set_article(intro)
                tn_html += intro

            chapter_chunk_data = {}
            previous_first_verse = None
            for idx, first_verse in enumerate(chapter_verses['first_verses']):
                if idx < len(chapter_verses['first_verses'])-1:
                    last_verse = chapter_verses['first_verses'][idx+1] - 1
                else:
                    last_verse = int(BOOK_CHAPTER_VERSES[self.project_id][chapter])
                self.logger.info(f'Generating chunk {chapter}:{first_verse}-{last_verse}...')

                chunk_notes = ''
                chunk_words = ''
                for verse in range(first_verse, last_verse + 1):
                    if str(verse) in self.tn_book_data[chapter]:
                        verse_notes = ''
                        tn_notes = self.get_tn_notes(chapter, verse)
                        for tn_note in tn_notes:
                            note = markdown2.markdown(tn_note['note'].replace('<br>', "\n"))
                            note = re.sub(r'</*p[^>]*>', '', note, flags=re.IGNORECASE | re.MULTILINE)
                            if first_verse != last_verse:
                                chapter_verse = f'({chapter}:{verse})'
                            else:
                                chapter_verse = ''
                            verse_notes += f'''
                <div class="verse-note">
                    <h3 class="verse-note-title">{tn_note['quote']} <span class="verse-note-reference">{chapter_verse}</span></h3>
                    <div class="verse-note-text">
                        {note}
                    </div>
                </div>
'''
                        chunk_notes += verse_notes

                        verse_words = f'<h3>{self.project_title} {chapter}:{verse}</h3>'
                        tw_words = self.get_tw_words(chapter, verse)
                        for tw_word in tw_words:
                            tw_rc_link = tw_word['contextId']['rc']
                            alignment = tw_word['text']
                            if tw_rc_link not in self.tw_rcs:
                                tw_rc = self.create_rc(tw_rc_link)
                                self.get_tw_article_html(tw_rc)
                                self.tw_rcs[tw_rc_link] = tw_rc
                            else:
                                tw_rc = self.tw_rcs[tw_rc_link]
                            verse_words += f'''
                <div class="verse-word">
                    <h4 class="verse-note-title">{tw_rc.title}</h4>
                    <div class="verse-note-text">
                        has been aligned as <em><a href="{tw_rc.rc_link}">{alignment}</a></em> 
                    </div>
                </div>
'''
                        chunk_words += verse_words

                chunk_notes = html_tools.decrement_headers(chunk_notes, 5)  # bring headers of 5 or more #'s down 1
                chunk_notes = self.fix_tn_links(chunk_notes, chapter)

                if previous_first_verse and \
                        (not chunk_notes or not chapter_chunk_data[previous_first_verse]['chunk_notes']):
                    if chunk_notes:
                        chapter_chunk_data[previous_first_verse]['chunk_notes'] = chunk_notes
                    chapter_chunk_data[previous_first_verse]['last_verse'] = last_verse
                else:
                    chapter_chunk_data[first_verse] = {
                        'chunk_notes': chunk_notes,
                        'chunk_words': chunk_words,
                        'first_verse': first_verse,
                        'last_verse': last_verse,
                    }
                    previous_first_verse = first_verse

            for first_verse in sorted(chapter_chunk_data.keys()):
                self.logger.info(f'Generating article from chunk data for {chapter}:{first_verse}...')
                tn_html += self.get_tn_chunk_article(chapter_chunk_data, chapter, first_verse)

        tn_html += "\n</section>\n\n"
        self.logger.info('Done generating tN HTML.')
        return tn_html

    def get_tn_chunk_article(self, chapter_chunk_data, chapter, first_verse):
        last_verse = chapter_chunk_data[first_verse]['last_verse']
        chunk_notes = chapter_chunk_data[first_verse]['chunk_notes']
        tn_title = f'{self.project_title} {chapter}:{first_verse}'
        if first_verse != last_verse:
            tn_title += f'-{last_verse}'
        tn_chunk_rc_link = f'rc://{self.lang_code}/tn/help/{self.project_id}/{self.pad(chapter)}/{str(first_verse).zfill(3)}/{str(last_verse).zfill(3)}'
        tn_chunk_rc = self.add_rc(tn_chunk_rc_link, title=tn_title)
        # make an RC for all the verses in this chunk in case they are reference
        for verse in range(first_verse, last_verse + 1):
            verse_rc_link = f'rc://{self.lang_code}/tn/help/{self.project_id}/{self.pad(chapter)}/{str(verse).zfill(3)}'
            self.add_rc(verse_rc_link, title=tn_title, article_id=tn_chunk_rc.article_id)
            self.verse_to_chunk[self.pad(chapter)][str(verse).zfill(3)] = tn_title
        ult_with_tw_words = self.get_ult_with_tw_words(tn_chunk_rc, int(chapter), first_verse, last_verse)
        ult_with_tn_quotes = self.get_ult_with_tn_quotes(tn_chunk_rc, int(chapter), first_verse, last_verse)

        ust_scripture = self.get_plain_scripture(self.ust_id, int(chapter), first_verse, last_verse)
        if not ust_scripture:
            ust_scripture = '&nbsp;'
        scripture = f'''
                    <h3 class="bible-resource-title">{self.ult_id.upper()}</h3>
                    <div class="bible-text">{ult_with_tw_words}</div>
                    <div class="bible-text hidden">{ult_with_tn_quotes}</div>
                    <h3 class="bible-resource-title">{self.ust_id.upper()}</h3>
                    <div class="bible-text">{ust_scripture}</div>
'''

        chunk_article = f'''
                <article id="{tn_chunk_rc.article_id}">
                    <h2 class="section-header">{tn_title}</h2>
                    <div class="tn-notes">
                            <div class="col1">
                                {scripture}
                            </div>
                            <div class="col2">
                                {chunk_notes}
                            </div>
                    </div>
                </article>
'''
        tn_chunk_rc.set_article(chunk_article)
        return chunk_article

    def populate_tw_words_data(self):
        groups = ['kt', 'names', 'other']
        if int(self.book_number) < 41:
            tw_path = self.uhb_tw_dir
        else:
            tw_path = self.ugnt_tw_dir
        if not os.path.isdir(tw_path):
            self.logger.error(f'{tw_path} not found!')
            exit(1)
        words = {}
        for group in groups:
            files_path = os.path.join(tw_path, f'{group}/groups/{self.project_id}', '*.json')
            files = glob(files_path)
            for file in files:
                base = os.path.splitext(os.path.basename(file))[0]
                tw_rc_link = f'rc://{self.lang_code}/tw/dict/bible/{group}/{base}'
                occurrences = load_json_object(file)
                for occurrence in occurrences:
                    context_id = occurrence['contextId']
                    chapter = context_id['reference']['chapter']
                    verse = context_id['reference']['verse']
                    context_id['rc'] = tw_rc_link
                    if chapter not in words:
                        words[chapter] = {}
                    if verse not in words[chapter]:
                        words[chapter][verse] = []
                    words[chapter][verse].append(context_id)
        self.tw_words_data = words

    def get_plain_scripture(self, resource, chapter, first_verse, last_verse=None):
        verses = ''
        footnotes = ''
        if not last_verse:
            last_verse = first_verse
        while first_verse <= last_verse:
            data = self.chunks_text[str(chapter)][str(first_verse)]
            footnotes_split = re.compile('<div class="footnotes">', flags=re.IGNORECASE | re.MULTILINE)
            verses_and_footnotes = re.split(footnotes_split, data[resource]['html'], maxsplit=1)
            verses += verses_and_footnotes[0]
            if len(verses_and_footnotes) == 2:
                footnote = f'<div class="footnotes">{verses_and_footnotes[1]}'
                if footnotes:
                    footnote = footnote.replace('<hr class="footnotes-hr"/>', '')
                footnotes += footnote
            first_verse = data['last_verse'] + 1
        html = ''
        if verses:
            verses = re.sub(r'\s*<span class="v-num"', '</div><div class="verse"><span class="v-num"', verses, flags=re.IGNORECASE | re.MULTILINE)
            verses = re.sub(r'^</div>', '', verses)
            if verses and '<div class="verse">' in verses:
                verses += '</div>'
            html = verses + footnotes
            html = re.sub(r'\s*\n\s*', ' ', html, flags=re.IGNORECASE | re.MULTILINE)
            html = re.sub(r'\s*</*p[^>]*>\s*', ' ', html, flags=re.IGNORECASE | re.MULTILINE)
            html = html.strip()
            html = re.sub('id="(ref-)*fn-', rf'id="{resource}-\1fn-', html,
                          flags=re.IGNORECASE | re.MULTILINE)
            html = re.sub('href="#(ref-)*fn-', rf'href="#{resource}-\1fn-', html,
                          flags=re.IGNORECASE | re.MULTILINE)
        return html

    def get_ult_with_tw_words(self, rc, chapter, first_verse, last_verse, ignore_small_words=True):
        html = self.get_plain_scripture(self.ult_id, chapter, first_verse, last_verse)
        footnotes_split = re.compile('<div class="footnotes">', flags=re.MULTILINE | re.IGNORECASE)
        verses_and_footnotes = footnotes_split.split(html, maxsplit=1)
        verses_html = verses_and_footnotes[0]
        footer_html = ''
        if len(verses_and_footnotes) == 2:
            footer_html = f'<div class="footnotes">{verses_and_footnotes[1]}'
        regex = re.compile(rf'<div class="verse"><span class="v-num" id="{self.ult_id}-\d+-ch-\d+-v-\d+"><sup><strong>(\d+)</strong></sup></span>')
        verses_split = regex.split(verses_html)
        verses = {}
        for i in range(1, len(verses_split), 2):
            verses[int(verses_split[i])] = verses_split[i+1]
        new_html = verses_split[0]
        for verse_num in range(first_verse, last_verse+1):
            if verse_num in verses:
                verse_html = verses[verse_num]
                words = self.get_tw_words(chapter, verse_num)
                sorted_words = sorted(words, key=lambda w: w['text'], reverse=True)
                orig_verse_html = verse_html
                for word in sorted_words:
                    tw_rc = word['contextId']['rc']
                    occurrence = word['contextId']['occurrence']
                    marked_verse_html = html_tools.mark_phrase_in_text(verse_html, word['text'],
                                                                       occurrence=occurrence,
                                                                       tag=f'<a href="{tw_rc}">',
                                                                       ignore_small_words=ignore_small_words)
                    if not marked_verse_html:
                        fix = html_tools.find_quote_variation_in_text(orig_verse_html, word['text'],
                                                                      occurrence=occurrence,
                                                                      ignore_small_words=ignore_small_words)
                        if not fix and occurrence > 1:
                            marked_verse_html = html_tools.mark_phrase_in_text(verse_html, word['text'],
                                                                               occurrence=1,
                                                                               ignore_small_words=ignore_small_words)
                            if marked_verse_html:
                                fix = f'(occurrence = {occurrence}, only occurrence 1 is found)'
                        self.add_bad_highlight(rc, orig_verse_html, tw_rc, word['text'], fix)
                    else:
                        verse_html = marked_verse_html
                new_html += f'''
        <div class="verse">
            <span class="v-num">
                <sup><strong>{verse_num}</strong></sup>
            </span>{verse_html}
'''
        new_html += footer_html
        return new_html

    def get_tw_words(self, chapter, verse):
        ult_package_dir = os.path.join(self.resources['ult'].repo_dir + '_' + self.resources['ult'].tag + '_package')
        chapter_json_path = f'{ult_package_dir}/{self.project_id}/{chapter}.json'
        words = []
        data = load_json_object(chapter_json_path)
        chapter = int(chapter)
        if chapter in self.tw_words_data and verse in self.tw_words_data[chapter]:
            context_ids = self.tw_words_data[int(chapter)][int(verse)]
            verse_objects = data[str(verse)]['verseObjects']
            for context_id in context_ids:
                aligned_text = self.get_aligned_text(verse_objects, context_id)
                if aligned_text:
                    words.append({'text': aligned_text, 'contextId': context_id})
        return words

    def get_ult_with_tn_quotes(self, rc, chapter, first_verse, last_verse):
        html = self.get_plain_scripture(self.ult_id, chapter, first_verse, last_verse)
        footnotes_split = re.compile('<div class="footnotes">', flags=re.MULTILINE | re.IGNORECASE)
        verses_and_footnotes = footnotes_split.split(html, maxsplit=1)
        verses_html = verses_and_footnotes[0]
        footer_html = ''
        if len(verses_and_footnotes) == 2:
            footer_html = f'<div class="footnotes">{verses_and_footnotes[1]}'
        regex = re.compile(rf'<div class="verse"><span class="v-num" id="{self.ult_id}-\d+-ch-\d+-v-\d+"><sup><strong>(\d+)</strong></sup></span>')
        verses_split = regex.split(verses_html)
        verses = {}
        for i in range(1, len(verses_split), 2):
            verses[int(verses_split[i])] = verses_split[i+1]
        new_html = verses_split[0]
        for verse_num in range(first_verse, last_verse+1):
            if verse_num in verses:
                verse_html = verses[verse_num]
                tn_notes = self.get_tn_notes(chapter, verse_num)
                sorted_tn_notes = sorted(tn_notes, key=lambda w: w['quote'], reverse=True)
                orig_verse_html = verse_html
                for tn_note in sorted_tn_notes:
                    tn_rc_link = f'rc://{self.lang_code}/tn/help/{self.project_id}/{self.pad(chapter)}/{str(verse_num).zfill(3)}'
                    marked_verse_html = html_tools.mark_phrase_in_text(verse_html, tn_note['quote'])
                    if not marked_verse_html and tn_note['quote'].lower() not in QUOTES_TO_IGNORE:
                        fix = html_tools.find_quote_variation_in_text(orig_verse_html, tn_note['quote'])
                        self.add_bad_highlight(rc, orig_verse_html, tn_rc_link, tn_note['quote'], fix)
                    else:
                        verse_html = marked_verse_html
                new_html += f'''
        <div class="verse">
            <span class="v-num">
                <sup><strong>{verse_num}</strong></sup>
            </span>{verse_html}
'''
        new_html += footer_html
        return new_html

    def get_tn_notes(self, chapter, verse):
        notes = []
        chapter = str(chapter)
        verse = str(verse)
        if chapter in self.tn_book_data and str(verse) in self.tn_book_data[chapter]:
            for data in self.tn_book_data[chapter][str(verse)]:
                note = {
                    'quote': data['GLQuote'],
                    'note': data['OccurrenceNote']
                }
                notes.append(note)
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
                        word_list[idx]['target'] += ' ... ' + target
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
                if ((('content' in verse_object and verse_object['content'] in words_to_match) or ('lemma' in verse_object and verse_object['lemma'] in words_to_match)) and verse_object['occurrence'] == occurrence) or is_match:
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

    def get_aligned_text(self, verse_objects, context_id):
        if not verse_objects or not context_id or 'quote' not in context_id or not context_id['quote']:
            return ''
        text = self.find_target_from_combination(verse_objects, context_id['quote'], context_id['occurrence'])
        if text:
            return text
        text = self.find_target_from_split(verse_objects, context_id['quote'], context_id['occurrence'])
        if text:
            return text
        chapter = context_id['reference']['chapter']
        verse = context_id['reference']['verse']
        title = f'{self.project_title} {chapter}:{verse}'
        aligned_text_rc_link = f'rc://{self.lang_code}/{self.ult_id}/bible/{self.project_id}/{self.pad(chapter)}/{str(verse).zfill(3)}'
        aligned_text_rc = self.create_rc(aligned_text_rc_link, title=title)
        if int(self.book_number) > 40 or self.project_id.lower() == 'rut' or self.project_id.lower() == 'jon':
            if int(self.book_number) < 41:
                bad_rc_lang = 'hbo'
            else:
                bad_rc_lang = 'el-x-koine'
            quote = context_id['quote']
            occurrence = context_id['occurrence']
            bad_rc_link = f'rc://{bad_rc_lang}/tw/word/{quote}/{occurrence}'
            self.add_bad_link(aligned_text_rc, bad_rc_link, fix=context_id['rc'])
            self.logger.error(f'{self.lang_code.upper()} WORD NOT FOUND FOR OL WORD `{quote}` (occurrence: {occurrence}) IN `ULT {title}`')

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
                # links to another chunk in another chapter
                link = os.path.splitext(link)[0]
                parts = link.split('/')
                if len(parts) == 3:
                    # should have two numbers, the chapter and the verse
                    c = parts[1]
                    v = parts[2]
                    new_link = f'rc://{self.lang_code}/tn/help/{self.project_id}/{self.pad(c)}/{v.zfill(3)}'
                if len(parts) == 2:
                    # shouldn't be here, but just in case, assume link to the first chunk of the given chapter
                    c = parts[1]
                    new_link = f'rc://{self.lang_code}/tn/help/{self.project_id}/{self.pad(c)}/001'
            elif link.startswith('./'):
                # link to another verse in the same chapter
                link = os.path.splitext(link)[0]
                parts = link.split('/')
                v = parts[1]
                new_link = f'rc://{self.lang_code}/tn/help/{self.project_id}/{self.pad(chapter)}/{v.zfill(3)}'
            return f'<a{before_href}href="{new_link}"{after_href}>{linked_text}</a>'
        regex = re.compile(r'<a([^>]+)href="(\.[^"]+)"([^>]*)>(.*?)</a>')
        html = regex.sub(replace_link, html)
        return html

    def get_chunk_html(self, usfm, resource, chapter, verse):
        usfm_chunks_path = os.path.join(self.working_dir, 'usfm_chunks',
                                        f'usfm-{self.lang_code}-{resource}-{self.project_id}-{chapter}-{verse}')
        filename_base = f'{resource}-{self.project_id}-{chapter}-{verse}'
        html_file = os.path.join(usfm_chunks_path, f'{filename_base}.html')
        usfm_file = os.path.join(usfm_chunks_path, f'{filename_base}.usfm')
        if not os.path.exists(usfm_chunks_path):
            os.makedirs(usfm_chunks_path)
        usfm = rf'''\id {self.project_id.upper()}
\ide UTF-8
\h {self.project_title}
\mt {self.project_title}

\c {chapter}
{usfm}'''
        write_file(usfm_file, usfm)
        UsfmTransform.buildSingleHtml(usfm_chunks_path, usfm_chunks_path, filename_base)
        html = read_file(os.path.join(usfm_chunks_path, filename_base+'.html'))
        soup = BeautifulSoup(html, 'html.parser')
        header = soup.find('h1')
        if header:
            header.decompose()
        chapter = soup.find('h2')
        if chapter:
            chapter.decompose()
        for span in soup.find_all('span', {'class': 'v-num'}):
            span['id'] = f"{resource}-{span['id']}"
        html = ''.join(['%s' % x for x in soup.body.contents])
        write_file(html_file, html)
        return html

    def get_ggo_back_to_html(self, source_rc):
        if source_rc.linking_level == 0:
            return ''
        go_back_tos = []
        done = {}
        book_started = False
        for rc_link in source_rc.references:
            if rc_link in self.rcs:
                rc = self.rcs[rc_link]
                chapter = rc.chapter
                verse = rc.verse
                if chapter == 'front':
                    if chapter in self.verse_to_chunk and verse in self.verse_to_chunk[chapter]:
                        text = self.verse_to_chunk[chapter][verse]
                    else:
                        text = 'Intro to {0}'.format(self.project_title)
                        self.verse_to_chunk[chapter][verse] = text
                elif verse == 'intro':
                    if chapter in self.verse_to_chunk and verse in self.verse_to_chunk[chapter]:
                        text = self.verse_to_chunk[chapter][verse]
                    else:
                        text = '{0} {1} Notes'.format(self.project_title, chapter)
                        self.verse_to_chunk[chapter][verse] = text
                    book_started = True
                else:
                    if chapter in self.verse_to_chunk and verse in self.verse_to_chunk[chapter]:
                        if book_started:
                            text = self.verse_to_chunk[chapter][verse].split(' ')[-1]
                        else:
                            text = self.verse_to_chunk[chapter][verse]
                    else:
                        text = '{0} {1}:{2}'.format(self.project_title, chapter.lstrip('0'), verse.lstrip('0'))
                        self.verse_to_chunk[chapter][verse] = text
                    book_started = True
                if text and self.verse_to_chunk[chapter][verse] not in done:
                    go_back_tos.append('<a href="#{0}">{1}</a>'.format(rc.article_id, text))
                done[self.verse_to_chunk[chapter][verse]] = True
                done[rc_link] = True
        go_back_to_html = ''
        if len(go_back_tos):
            go_back_tos_string = '; '.join(go_back_tos)
            go_back_to_html = f'''
    <div class="go-back-to">
        (<strong>{self.translate('go_back_to')}:</strong> {go_back_tos_string})
    </div>
'''
        return go_back_to_html


def main(tn_class):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--ust-id', dest='ust_id', default=DEFAULT_UST_ID, required=False, help="UST ID")
    parser.add_argument('--ult-id', dest='ult_id', default=DEFAULT_ULT_ID, required=False, help="ULT ID")
    run_converter(['tn', 'ult', 'ust', 'ta', 'tw', 'ugnt', 'uhb'], tn_class, all_project_ids=BOOK_NUMBERS.keys(), parser=parser)


if __name__ == '__main__':
    main(TnPdfConverter)
