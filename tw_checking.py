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
from general_tools.file_utils import load_json_object, get_latest_version_path, get_child_directories
from general_tools.html_tools import mark_phrases_in_html

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

    def get_body_html(self):
        self.add_style_sheet('css/tn_style.css')
        self.logger.info('Creating TW Checking for {0}...'.format(self.file_project_and_tag_id))
        self.populate_verse_usfm(self.ult_id)
        self.populate_verse_usfm(self.ust_id)
        self.populate_verse_usfm(self.ol_bible_id, self.ol_lang_code)
        return self.get_tw_checking_html()

    def get_tw_checking_html(self):
        tw_html = f'''
<section id="{self.lang_code}-{self.name}-{self.project_id}" class="{self.name}">
    <article id="{self.lang_code}-{self.name}-{self.project_id}-cover" class="resource-title-page">
        <img src="images/{self.main_resource.logo_file}" class="logo" alt="UTN">
        <h1 class="section-header">{self.title}</h1>
        <h2 class="section-header">{self.project_title}</h2>
    </article>
'''

        tw_path = os.path.join(self.working_dir, 'resources', self.ol_lang_code, 'translationHelps/translationWords')
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
        <h3 class="section-header">{tw_rc.title} ({tw_rc.rc_link})</h3>
        <table width="100%">
'''

                tw_group_data = load_json_object(file)
                for group_data in tw_group_data:
                    context_id = group_data['contextId']
                    context_id['rc'] = tw_rc.rc_link
                    chapter = str(context_id['reference']['chapter'])
                    verse = str(context_id['reference']['verse'])
                    for bible_id in [self.ult_id, self.ust_id]:
                        aligned_text = self.get_aligned_text(bible_id, context_id)
                        scripture = self.get_plain_scripture(bible_id, chapter, verse)
                        marked_html = None
                        if aligned_text:
                            marked_html = mark_phrases_in_html(scripture, aligned_text, ignore_small_words=False)
                        if marked_html:
                            context_id[f'{bible_id}Text'] = marked_html
                        else:
                            context_id[f'{bible_id}Text'] = scripture
                        context_id[f'{bible_id}Quote'] = aligned_text
                    scripture = self.get_plain_scripture(self.ol_bible_id, chapter, verse)
                    quotes = context_id['quote']
                    if isinstance(quotes, str):
                        quotes = [{'word': quotes, 'occurrence': context_id['occurrence']}]
                    phrases = []
                    for quote in quotes:
                        phrases.append([quote])
                    marked_html = mark_phrases_in_html(scripture, phrases, ignore_small_words=False)
                    if marked_html:
                        context_id['olText'] = marked_html
                    else:
                        context_id['olText'] = scripture
                    tw_html += f'''
            <tr>
                <td>
                    {chapter}:{verse}
                </td>
                <td>
                    {context_id[f'{self.ult_id}Quote']}
                </td>
                <td>
                    {context_id[f'{self.ult_id}Text']}
                </td>
                <td>
                    {context_id[f'{self.ust_id}Quote']}
                </td>
                <td>
                    {context_id[f'{self.ust_id}Text']}
                </td>
                <td dir="{'rtl' if self.ol_lang_code == 'hbo' else 'ltr'}">
                    {context_id['quote']}
                </td>
                <td dir="{'rtl' if self.ol_lang_code == 'hbo' else 'ltr'}">
                    {context_id['olText']}
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
        self.logger.info('Done generating tW Checking HTML.')
        return tw_html


if __name__ == '__main__':
    main(TwCheckingPdfConverter, ['ult', 'ust', 'ta', 'tw', 'ugnt', 'uhb'])
