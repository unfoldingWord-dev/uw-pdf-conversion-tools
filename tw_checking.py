#!/usr/bin/env python3
#
#  Copyright (c) 2020 unfoldingWord
#  http://creativecommons.org/licenses/MIT/
#  See LICENSE file for details.
#
#  Contributors:
#  Richard Mahn <rich.mahn@unfoldingword.org>

"""
This script generates the TW Word checking PDF
"""
import os
from glob import glob
from tn_pdf_converter import TnPdfConverter, main
from general_tools.file_utils import load_json_object, get_latest_version_path, get_child_directories
from general_tools.html_tools import mark_phrases_in_html
from general_tools.alignment_tools import flatten_alignment, split_string_into_alignment, convert_single_dimensional_quote_to_multidimensional

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
    def title(self):
        return self.main_resource.title + ' - Checking'

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
        self.logger.info('Creating TW Checking for {0}...'.format(self.file_project_and_ref))
        self.add_style_sheet('../css/tn_style.css')
        self.process_bibles()
        self.populate_book_data(self.ult_id)
        self.populate_book_data(self.ust_id)
        self.populate_book_data(self.ol_bible_id, self.ol_lang_code)
        return self.get_tw_checking_html()

    def get_tw_checking_html(self):
        tw_html = f'''
<section id="{self.lang_code}-{self.name}-{self.project_id}" class="{self.name}">
    <article id="{self.lang_code}-{self.name}-{self.project_id}-cover" class="resource-title-page">
        <img src="{self.main_resource.logo_url}" class="logo" alt="UTW">
        <h1 class="section-header">{self.title}</h1>
        <h2 class="section-header">{self.project_title}</h2>
    </article>
'''

        tw_path = os.path.join(self.resources_dir, self.ol_lang_code, 'translationHelps/translationWords')
        if not tw_path:
            self.logger.error(f'{tw_path} not found!')
            exit(1)
        tw_version_path = get_latest_version_path(tw_path)
        if not tw_version_path:
            self.logger.error(f'No versions found in {tw_path}!')
            exit(1)

        groups = get_child_directories(tw_version_path)
        for group in groups:
            files_path = os.path.join(tw_version_path, f'{group}/groups/{self.project_id}', '*.json')
            files = glob(files_path)
            for file in files:
                base = os.path.splitext(os.path.basename(file))[0]
                tw_rc_link = f'rc://{self.lang_code}/tw/dict/bible/{group}/{base}'
                tw_rc = self.add_rc(tw_rc_link, title=base)
                self.get_tw_article_html(tw_rc)
                tw_html += f'''
    <article id="{tw_rc.article_id}">
        <h3 class="section-header">[[{tw_rc.rc_link}]]</h3>
        <table width="100%">
            <tr>
               <th style="width:1px;padding:0 !important"></th>
               <th>Verse</th>
               <th>{self.ult_id.upper()} Alignment</th>
               <th>{self.ult_id.upper()} Text</th>
               <th>{self.ust_id.upper()} Alignment</th>
               <th>{self.ust_id.upper()} Text</th>
               <th>{self.ol_bible_id.upper()} Quote</th>
               <th>{self.ol_bible_id.upper()} Text</th>
            </tr>
'''

                tw_group_data = load_json_object(file)
                for group_data in tw_group_data:
                    context_id = group_data['contextId']
                    context_id['rc'] = tw_rc.rc_link
                    chapter = str(context_id['reference']['chapter'])
                    verse = str(context_id['reference']['verse'])
                    context_id['scripture'] = {}
                    context_id['alignments'] = {}
                    for bible_id in [self.ult_id, self.ust_id]:
                        alignment = self.get_aligned_text(bible_id, group_data['contextId'])
                        if alignment:
                            context_id['alignments'][bible_id] = flatten_alignment(alignment)
                        else:
                            context_id['alignments'][bible_id] = '<div style="color: red">NONE</div>'
                        scripture = self.get_plain_scripture(bible_id, chapter, verse)
                        marked_html = None
                        if alignment:
                            marked_html = mark_phrases_in_html(scripture, alignment)
                        if marked_html:
                            context_id['scripture'][bible_id] = marked_html
                        else:
                            context_id['scripture'][bible_id] = f'<div style="color: red">{scripture}</div>'
                    scripture = self.get_plain_scripture(self.ol_bible_id, chapter, verse)
                    ol_alignment = context_id['quote']
                    if isinstance(ol_alignment, str):
                        ol_alignment = split_string_into_alignment(ol_alignment)
                    if not isinstance(ol_alignment[0], list):
                        ol_alignment = convert_single_dimensional_quote_to_multidimensional(ol_alignment)
                    marked_html = mark_phrases_in_html(scripture, ol_alignment)
                    if marked_html:
                        context_id['scripture'][self.ol_bible_id] = marked_html
                    else:
                        context_id['scripture'][self.ol_bible_id] = f'<div style="color: red">{scripture}</div>'
                    tw_html += f'''
            <tr id="{tw_rc.article_id}-{chapter}-{verse}">
                <td style="width:1px;padding:0 !important"><a href="#{tw_rc.article_id}-{chapter}-{verse}"><i class="fa fa-link"></i></td>
                <td>
                    {chapter}:{verse}
                </td>
                <td>
                    {context_id['alignments'][self.ult_id]}
                </td>
                <td>
                    {context_id['scripture'][self.ult_id]}
                </td>
                <td>
                    {context_id['alignments'][self.ust_id]}
                </td>
                <td>
                    {context_id['scripture'][self.ust_id]}
                </td>
                <td style="direction: {'rtl' if self.ol_lang_code == 'hbo' else 'ltr'}">
                    {flatten_alignment(ol_alignment)}
                </td>
                <td style="direction: {'rtl' if self.ol_lang_code == 'hbo' else 'ltr'}">
                    {context_id['scripture'][self.ol_bible_id]}
                </td>
            </tr>
'''
                tw_html += '''
        </table>
    </article>
'''

        tw_html += '''
</section>
'''
        self.logger.info('Done generating TW Checking HTML.')
        return tw_html


if __name__ == '__main__':
    main(TwCheckingPdfConverter, ['tw', 'ult', 'ust', 'ugnt', 'uhb'])
