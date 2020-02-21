#!/usr/bin/env python3
#
#  Copyright (c) 2020 unfoldingWord
#  http://creativecommons.org/licenses/MIT/
#  See LICENSE file for details.
#
#  Contributors:
#  Richard Mahn <rich.mahn@unfoldingword.org>

"""
This script generates the TN checking PDF
"""
import os
from glob import glob
from tn_pdf_converter import TnPdfConverter, main
from general_tools.file_utils import load_json_object, get_latest_version_path, get_child_directories
from general_tools.html_tools import mark_phrases_in_html
from general_tools.alignment_tools import flatten_alignment, flatten_quote, split_string_into_quote

ORDERED_GROUPS = {
    'kt': 'Key Terms',
    'names': 'Names',
    'other': 'Other'
}


class TnCheckingPdfConverter(TnPdfConverter):

    @property
    def name(self):
        return 'tn-checking'

    @property
    def title(self):
        return self.main_resource.title + ' - Checking'

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

    def generate_pdf(self):
        pass

    def get_contributors_html(self):
        return ''

    def get_license_html(self):
        return ''

    def download_all_images(self, html):
        return html

    @staticmethod
    def _fix_links(html):
        return html

    def fix_links(self, html):
        return html

    def get_body_html(self):
        self.add_style_sheet('css/tn_style.css')
        self.logger.info('Creating TN Checking for {0}...'.format(self.file_project_and_tag_id))
        self.populate_verse_usfm(self.ult_id)
        self.populate_verse_usfm(self.ust_id)
        self.populate_verse_usfm(self.ol_bible_id, self.ol_lang_code)
        return self.get_tn_checking_html()

    def get_tn_checking_html(self):
        self.populate_tn_groups_data()
        self.populate_tn_book_data()

        by_rc_cat_group = {}
        for chapter in self.tn_book_data:
            for verse in self.tn_book_data[chapter]:
                for data in self.tn_book_data[chapter][verse]:
                    if data['contextId']:
                        rc_link = data['contextId']['rc']
                        parts = rc_link[5:].split('/')
                        category = parts[3]
                        group = parts[4]
                        if category not in by_rc_cat_group:
                            by_rc_cat_group[category] = {}
                        if group not in by_rc_cat_group[category]:
                            by_rc_cat_group[category][group] = []
                        by_rc_cat_group[category][group].append(data)

        tn_html = f'''
<section id="{self.lang_code}-{self.name}-{self.project_id}" class="{self.name}">
    <article id="{self.lang_code}-{self.name}-{self.project_id}-cover" class="resource-title-page">
        <img src="images/{self.main_resource.logo_file}" class="logo" alt="UTN">
        <h1 class="section-header">{self.title}</h1>
        <h2 class="section-header">{self.project_title}</h2>
    </article>
'''

        categories = sorted(by_rc_cat_group.keys())
        for category in categories:
            groups = sorted(by_rc_cat_group[category].keys())
            for group in groups:
                tn_rc_link = f'rc://{self.lang_code}/tn/help/{category}/{group}'
                tn_rc = self.add_rc(tn_rc_link, title=f'{group} ({category})')
                tn_html += f'''
    <article id="{tn_rc.article_id}">
        <h3 class="section-header">Support Reference: [[{tn_rc.rc_link}]]</h3>
        <table width="100%">
            <tr>
               <th>Verse</th>
               <th>{self.ult_id.upper()} Alignment</th>
               <th>{self.ult_id.upper()} Text</th>
               <th>{self.ust_id.upper()} Alignment</th>
               <th>{self.ust_id.upper()} Text</th>
               <th>{self.ol_bible_id.upper()} Quote</th>
               <th>{self.ol_bible_id.upper()} Text</th>
            </tr>
'''
                for group_data in by_rc_cat_group[category][group]:
                    context_id = group_data['contextId']
                    context_id['rc'] = tn_rc.rc_link
                    chapter = str(context_id['reference']['chapter'])
                    verse = str(context_id['reference']['verse'])
                    group_data['scripture'] = {}
                    for bible_id in [self.ult_id, self.ust_id]:
                        alignment = group_data['alignments'][bible_id]
                        if not alignment:
                            group_data['alignments'][bible_id] = '<div style="color: red">NONE</div>'
                        else:
                            group_data['alignments'][bible_id] = flatten_alignment(alignment)
                        scripture = self.get_plain_scripture(bible_id, chapter, verse)
                        marked_html = None
                        if alignment:
                            marked_html = mark_phrases_in_html(scripture, alignment)
                        if marked_html:
                            group_data['scripture'][bible_id] = marked_html
                        else:
                            group_data['scripture'][bible_id] = f'<div style="color: red">{scripture}</div>'
                    scripture = self.get_plain_scripture(self.ol_bible_id, chapter, verse)
                    ol_quote = context_id['quote']
                    if isinstance(ol_quote, str):
                        ol_quote = split_string_into_quote(ol_quote)
                    phrases = []
                    for word in ol_quote:
                        if 'word' in word and 'occurrence' in word and word['word'] != '…':
                            phrases.append([{
                                'text': word['word'],
                                'occurrence': word['occurrence']
                            }])
                    break_on_word = True
                    if self.ol_lang_code == 'hbo':
                        break_on_word = False
                    marked_html = mark_phrases_in_html(scripture, phrases, break_on_word=break_on_word)
                    if marked_html:
                        group_data['scripture'][self.ol_bible_id] = marked_html
                    else:
                        group_data['scripture'][self.ol_bible_id] = f'<div style="color: red">{scripture}</div>'
                    tn_html += f'''
            <tr>
                <td>
                    {chapter}:{verse} ({group_data['ID']})
                </td>
                <td>
                    {group_data['alignments'][self.ult_id]}
                </td>
                <td>
                    {group_data['scripture'][self.ult_id]}
                </td>
                <td>
                    {group_data['alignments'][self.ust_id]}
                </td>
                <td>
                    {group_data['scripture'][self.ust_id]}
                </td>
                <td style="direction: {'rtl' if self.ol_lang_code == 'hbo' else 'ltr'}">
                    {flatten_quote(ol_quote)}
                </td>
                <td style="direction: {'rtl' if self.ol_lang_code == 'hbo' else 'ltr'}">
                    {group_data['scripture'][self.ol_bible_id]}
                </td>
            </tr>
'''
                tn_html += '''
        </table>
    </article>
'''

        tn_html += '''
</section>
'''
        self.logger.info('Done generating TN Checking HTML.')
        return tn_html


if __name__ == '__main__':
    main(TnCheckingPdfConverter, ['tn', 'ult', 'ust', 'ugnt', 'uhb'])
