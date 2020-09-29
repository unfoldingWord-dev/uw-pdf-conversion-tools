#!/usr/bin/env python3
#
#  Copyright (c) 2020 unfoldingWord
#  http://creativecommons.org/licenses/MIT/
#  See LICENSE file for details.
#
#  Contributors:
#  Richard Mahn <rich.mahn@unfoldingword.org>

"""
This script generates the HTML and PDF for a given Bible
"""
import os
import re
import argparse
from bs4 import BeautifulSoup
from pdf_converter import PdfConverter, run_converter
from general_tools.bible_books import BOOK_NUMBERS
from general_tools.file_utils import read_file
from general_tools.usfm_utils import unalign_usfm
from tx_usfm_tools.singleFilelessHtmlRenderer import SingleFilelessHtmlRenderer

DEFAULT_ULT_ID = 'ult'


class BiblePdfConverter(PdfConverter):
    def __init__(self, bible_id, chapter=None, *args, **kwargs):
        self.project_id = kwargs['project_id']
        self.bible_id = bible_id
        self.chapter = chapter
        self.chapters = self.parse_chapters(chapter)
        super().__init__(*args, **kwargs)

    @property
    def book_number(self):
        if self.project_id and self.project_id not in ['all', 'ot', 'nt']:
            return BOOK_NUMBERS[self.project_id]

    @staticmethod
    def parse_chapters(chapter):
        chapters = []
        if chapter:
            comma_nums = chapter.split(',')
            for nums in comma_nums:
                dash_nums = nums.split('-')
                start_num = int(dash_nums[0])
                if len(dash_nums) > 1:
                    end_num = int(dash_nums[-1]) + 1
                else:
                    end_num = start_num + 1
                for num in range(start_num, end_num):
                    chapters.append(num)
        return chapters

    @property
    def file_id_project_str(self):
        if self.project_id and self.project_id != 'all':
            chapter_str = f'-{self.pad(self.chapter)}' if self.chapter else ''
            book_number_str = f'{self.book_number.zfill(2)}-' if self.project_id not in ['ot', 'nt'] else ''
            return f'_{book_number_str}{self.project_id.upper()}{chapter_str}'
        else:
            return ''

    @property
    def project_title(self):
        if not self.project_id or self.project_id == 'all':
            return ''
        elif self.project_id == 'ot':
            return self.translate('old_testament')
        elif self.project_id == 'nt':
            return self.translate('new_testament')
        else:
            project = self.project
            if project:
                return project['title']

    def get_appendix_rcs(self):
        pass

    def replace_rc_links(self, text):
        return text

    def get_body_html(self):
        self.logger.info('Creating Bible for {0}...'.format(self.file_project_and_ref))
        self.add_style_sheet('../css/bible_style.css')
        return self.get_bible_html()

    def get_book_title(self, project):
        if self.main_resource.title in project['title']:
            return project['title'].replace(f' {self.main_resource.title}', '')
        else:
            return project['title'].replace(f' {self.main_resource.simple_title}', '')

    def get_bible_html(self):
        if not self.project_id:
            self.project_id = 'all'
        if self.project_id == 'all':
            projects = self.main_resource.projects
        else:
            if self.project_id == 'ot' or self.project_id == 'nt':
                first_book = int(BOOK_NUMBERS['gen']) - 1
                last_book = int(BOOK_NUMBERS['rev']) - 1
                if self.project_id == 'ot':
                    last_book = int(BOOK_NUMBERS['mal'])
                else:
                    first_book = int(BOOK_NUMBERS['mat']) - 2
                project_ids = list(BOOK_NUMBERS.keys())[first_book:last_book]
            else:
                project_ids = [self.project_id]
            projects = [self.main_resource.find_project(project_id) for project_id in project_ids]
        bible_html = f'''
<section id="{self.lang_code}-{self.name}" class="bible {self.name}-bible bible-{self.project_id} {self.name}-bible-{self.project_id}">
'''
        for project_idx, project in enumerate(projects):
            project_id = project['identifier']
            project_num = BOOK_NUMBERS[project_id]
            project_file = os.path.join(self.main_resource.repo_dir, f'{project_num}-{project_id.upper()}.usfm')
            usfm = read_file(project_file)
            usfm = unalign_usfm(usfm)
            if self.chapters:
                usfm_split = re.split(r'\\c ', usfm)
                usfm = usfm_split[0]
                for chapter in self.chapters:
                    usfm += '\\c ' + usfm_split[chapter]
            self.logger.info(f'Converting {project_id.upper()} from USFM to HTML...')
            html, warnings = SingleFilelessHtmlRenderer({project_id.upper(): usfm}).render()
            soup = BeautifulSoup(html, 'html.parser')
            book_header = soup.find('h1')
            book_title = book_header.text
            book_header['class'] = book_header.get('class', []) + ['section-header']
            book_header['header_title'] = self.title
            chapter_headers = soup.find_all('h2')
            for chapter_header in chapter_headers:
                chapter_title = chapter_header.text
                chapter = re.search(r'\d+', chapter_title).group()
                header_title = f'{book_title} {chapter}'
                classes = ['section-header']
                if len(projects) > 1:
                    classes += ['no-toc']
                chapter_header['class'] = chapter_header.get('class', []) + classes
                chapter_header['id'] = f'{self.lang_code}-{self.name}-{project_id}-{self.pad(chapter)}'
                chapter_header['header_title'] = header_title
            article_html = ''.join(['%s' % x for x in soup.body.contents]).strip()
            bible_html += f'''
    <article id="{self.lang_code}-{self.name}-{project_id}" class="bible-book bible-book-{project_id} {self.name}-bible-book">
        <div class="bible-book-wrapper">
            {article_html}
        </div>
    </article>
'''
        bible_html += '''
</section>
'''
        return bible_html

    def fix_links(self, html):
        html = re.sub(r' +(<span id="ref-fn-)', r'\1', html, flags=re.MULTILINE)
        html = re.sub(r'(</b></sup></span>) +', r'\1', html, flags=re.MULTILINE)
        html = re.sub(r' +(</i>)', r'\1', html, flags=re.MULTILINE)
        return html


def main(bible_class, resource_names=None):
    if not resource_names:
        resource_names = []
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-b', '--bible-id', dest='bible_id', default=DEFAULT_ULT_ID, required=False, help=f'Bible resource ID. Default: {DEFAULT_ULT_ID}')
    parser.add_argument('-c', '--chapter', dest='chapter', default=None, required=False, help=f'Chapter(s) to generate, can be a range, e.g. -c 1-3,5')
    parser.add_argument(f'--bible-ref', dest='bible_id_ref', default=None, required=False,
                        help=f'Branch or tag for the `bible_id`. If not set, uses latest tag unless --master flag is used')
    run_converter(resource_names, bible_class, project_ids_map={'': BOOK_NUMBERS.keys(), 'all': [None]},
                  parser=parser, extra_resource_id='bible_id')


if __name__ == '__main__':
    main(BiblePdfConverter)
