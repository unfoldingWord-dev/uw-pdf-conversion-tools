#!/usr/bin/env python3
#
#  Copyright (c) 2020 unfoldingWord
#  http://creativecommons.org/licenses/MIT/
#  See LICENSE file for details.
#
#  Contributors:
#  Richard Mahn <rich.mahn@unfoldingword.org>

"""
This script generates the TN Word checking PDF
"""
import os
from glob import glob
from tn_pdf_converter import TnPdfConverter, main
from general_tools.bible_books import BOOK_CHAPTER_VERSES
from general_tools.file_utils import load_json_object
from collections import OrderedDict

ORDERED_GROUPS = {
    'kt': 'Key Terms',
    'names': 'Names',
    'other': 'Other'
}

class TwCheckingPdfConverter(TnPdfConverter):

    @property
    def name(self):
        return 'tw-checking'

    @property
    def main_resource(self):
        return self.resources['tw']

    @property
    def project(self):
        if self.project_id:
            if not self._project:
                self._project = self.resources['ult'].find_project(self.project_id)
                if not self._project:
                    self.logger.error(f'Project not found: {self.project_id}')
                    exit(1)
            return self._project

    def get_appendix_rcs(self):
        pass

    def get_body_html(self):
        self.add_style_sheet('css/tn_style.css')
        self.logger.info('Creating TW Checking for {0}...'.format(self.file_project_and_tag_id))
        self.populate_tw_words_data()
        self.populate_verse_usfm(self.ult_id)
        self.populate_verse_usfm(self.ust_id)
        return self.get_tw_checking_html()

    def populate_tw_words_data(self):
        if int(self.book_number) < 41:
            tw_path = self.uhb_tw_dir
        else:
            tw_path = self.ugnt_tw_dir
        for group in ORDERED_GROUPS:
            self.tw_words_data[group] = {}
            files_path = os.path.join(tw_path, f'{group}/groups/{self.project_id}', '*.json')
            files = glob(files_path)
            for file in files:
                base = os.path.splitext(os.path.basename(file))[0]
                tw_rc_link = f'rc://{self.lang_code}/tw/dict/bible/{group}/{base}'
                tw_rc = self.create_rc(tw_rc_link)
                self.get_tw_article_html(tw_rc_link)
                self.tw_words_data[group][base] = {
                    'rc': tw_rc,
                    'data': []
                }
                occurrences = load_json_object(file)
                for occurrence in occurrences:
                    context_id = occurrence['contextId']
                    chapter = str(context_id['reference']['chapter'])
                    verse = str(context_id['reference']['verse'])
                    ult_package_dir = os.path.join(self.resources['ult'].repo_dir + '_' + self.resources['ult'].tag + '_package')
                    chapter_json_path = f'{ult_package_dir}/{self.project_id}/{chapter}.json'
                    data = load_json_object(chapter_json_path)
                    verse_objects = data[verse]['verseObjects']
                    aligned_text = self.get_aligned_text(verse_objects, context_id)
                    self.tw_words_data[group][base].append({
                        'occurrence': occurrence,
                        'aligned_text': aligned_text
                    })

    def get_tw_checking_html(self):
        tw_html = f'''
<section id="{self.lang_code}-{self.name}-{self.project_id}" class="{self.name}">
    <article id="{self.lang_code}-{self.name}-{self.project_id}-cover" class="resource-title-page">
        <img src="images/{self.main_resource.logo_file}" class="logo" alt="UTN">
        <h1 class="section-header">{self.title}</h1>
        <h2 class="section-header">{self.project_title}</h2>
    </article>
'''

        for group in ORDERED_GROUPS:
            tw_html = f'''
<section id="{self.lang_code}-{self.name}-{self.project_id}" class="{self.name}">
    <h3 class="section-header">{ORDERED_GROUPS[group]}</h3>
'''
            ordered_by_title = sorted(self.tw_words_data[group], key=lambda x: x['rc'].title)
            for filename in ordered_by_title:
                tw_html = f'''
                    <article id="{}"
'''

        for chapter in BOOK_CHAPTER_VERSES[self.project_id]:
            self.logger.info(f'Chapter {chapter}...')
            chapter_title = f'{self.project_title} {chapter}'
            # HANDLE INTRO RC LINK
            chapter_rc_link = f'rc://{self.lang_code}/{self.name}/help/{self.project_id}/{self.pad(chapter)}'
            chapter_rc = self.add_rc(chapter_rc_link, title=chapter_title)
            tw_html += f'''
    <section id="{chapter_rc.article_id}" class="tn-chapter">
        <h3 class="section-header">{chapter_title}</h3>
'''
            for verse in range(1,  int(BOOK_CHAPTER_VERSES[self.project_id][chapter]) + 1):
                verse = str(verse)
                self.logger.info(f'Generating verse {chapter}:{verse}...')
                tw_html += self.get_tw_checking_article(chapter, verse)
            tw_html += '''
    </section>
'''
        tw_html += '''
</section>
'''
        self.logger.info('Done generating tW Checking HTML.')
        return tw_html

    def get_tw_checking_article(self, chapter, verse):
        tw_title = f'{self.project_title} {chapter}:{verse}'
        tw_rc_link = f'rc://{self.lang_code}/{self.name}/help/{self.project_id}/{self.pad(chapter)}/{verse.zfill(3)}'
        tw_rc = self.add_rc(tw_rc_link, title=tw_title)
        tw_article = f'''
                <article id="{tw_rc.article_id}">
                    <h3 class="section-header no-toc">{tw_title}</h3>
                    <div class="tn-notes">
                            <div class="col1">
                                {self.get_scripture(chapter, verse, tw_rc)}
                            </div>
                            <div class="col2">
                                {self.get_tw_checking_article_text(chapter, verse)}
                            </div>
                    </div>
                </article>
'''
        tw_rc.set_article(tw_article)
        return tw_article

    def get_tw_checking_article_text(self, chapter, verse):
        verse_words = ''
        if verse in self.tw_words_data[chapter]:
            tw_words = self.get_tw_words(chapter, verse)
            for tw_word_idx, tw_word in enumerate(tw_words):
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
            <h3 class="verse-note-title">{tw_rc.title}</h3>
            <div class="verse-note-text">
                has been aligned as <em><a href="{tw_rc.rc_link}" class="tw-phrase-{tw_word_idx + 1}">{alignment}</a></em> 
            </div>
        </div>
'''
        return verse_words


if __name__ == '__main__':
    main(TwCheckingPdfConverter, ['ult', 'ust', 'ta', 'tw', 'ugnt', 'uhb'])
