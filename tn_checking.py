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
import string
from tn_pdf_converter import TnPdfConverter, main
from general_tools.html_tools import mark_phrases_in_html
from general_tools.alignment_tools import flatten_alignment, split_string_into_alignment
from general_tools.file_utils import write_file, symlink

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
        self.logger.info('Creating TN Checking for {0}...'.format(self.file_project_and_ref))
        self.add_style_sheet('../css/tn_style.css')
        self.process_bibles()
        self.populate_book_data(self.ult_id)
        self.populate_book_data(self.ust_id)
        self.populate_book_data(self.ol_bible_id, self.ol_lang_code)
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
        <img src="{self.main_resource.logo_url}" class="logo" alt="UTN">
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
                    ol_alignment = split_string_into_alignment(group_data['OrigQuote'])
                    marked_html = mark_phrases_in_html(scripture, ol_alignment)
                    if marked_html:
                        group_data['scripture'][self.ol_bible_id] = marked_html
                    else:
                        marked_html = mark_phrases_in_html(scripture, ol_alignment, break_on_word=False)
                        if marked_html:
                            scripture = marked_html
                        group_data['scripture'][self.ol_bible_id] = f'<div style="color: red">{scripture}</div>'
                    tn_html += f'''
            <tr id="{group_data['rc'].article_id}">
                <td style="width:1px;padding:0 !important"><a id="{group_data['ID']}"></a><a href="#{group_data['rc'].article_id}"><i class="fa fa-link"></i></a></td>
                <td>
                    {chapter}:{verse}
                    (<a href="https://git.door43.org/unfoldingWord/{self.lang_code}_tn/src/branch/master/{self.lang_code}_tn_{self.book_number}-{self.project_id.upper()}.tsv#L{group_data['row']}" target="tn-repo">{group_data['ID']}</a>)
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
                    {group_data['OrigQuote']}
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

    def save_errors_html(self):
        save_file = os.path.join(self.output_res_dir, f'{self.file_project_and_unique_ref}_errors.html')
        link_file_path = os.path.join(self.output_res_dir, f'{self.file_project_and_ref}_errors_latest.html')

        if not self.errors:
            self.logger.info('No errors for this version!')
            if os.path.exists(save_file):
                os.unlink(save_file)
            if os.path.exists(link_file_path):
                os.unlink(link_file_path)
            return

        errors_html = '''
<h1>ERRORS</h1>
<ul>
'''
        for source_rc_link in sorted(self.errors.keys()):
            parts = source_rc_link[5:].split('/')
            book = parts[3]
            chapter = parts[4]
            verse = parts[5]
            tn_id = parts[6]
            source_rc = self.errors[source_rc_link]['source_rc']
            errors = self.errors[source_rc_link]['errors']
            for rc_link in sorted(errors.keys()):
                errors_html += f'''
    <li>
        TN NOTE 
        <a href="{os.path.basename(self.html_file)}#{source_rc.article_id}" title="See in the HTML" target="{self.name}-html">
            {book} {chapter}:{verse} - {tn_id}
        </a>:
'''
                if rc_link.startswith('rc://'):
                    errors_html += f'''
        BAD RC LINK: `{rc_link}`'''
                else:
                    errors_html += f'''
        {rc_link}'''
                if errors[rc_link]:
                    message = errors[rc_link]
                else:
                    message = 'linked article not found'
                if '\n' in message:
                    message = f'<br/><pre>{message}</pre>'
                errors_html += f': {message}'
                errors_html += f'''
    </li>
'''
        errors_html += '''
</ul>
'''
        with open(os.path.join(self.converters_dir, 'templates/template.html')) as template_file:
            html_template = string.Template(template_file.read())
        html = html_template.safe_substitute(title=f'ERRORS FOR {self.file_project_and_unique_ref}', link='', body=errors_html)
        write_file(save_file, html)
        symlink(save_file, link_file_path, True)

        self.logger.info(f'ERRORS HTML file can be found at {save_file}')


if __name__ == '__main__':
    main(TnCheckingPdfConverter)
