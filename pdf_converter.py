#!/usr/bin/env python3
#
#  Copyright (c) 2020 unfoldingWord
#  http://creativecommons.org/licenses/MIT/
#  See LICENSE file for details.
#
#  Contributors:
#  Richard Mahn <rich.mahn@unfoldingword.org>

"""
Class for any resource PDF converter
"""
import os
import re
import logging
import tempfile
import markdown2
import shutil
import string
import sys
import argparse
import jsonpickle
import yaml
from cssutils import parseStyle
from cssutils.css import CSSStyleDeclaration
# import pypandoc
import json
import general_tools.html_tools as html_tools
from typing import List, Type
from bs4 import BeautifulSoup
from abc import abstractmethod
from weasyprint import HTML, CSS
from general_tools.file_utils import write_file, read_file, load_json_object, symlink, unzip
from general_tools.font_utils import get_font_html_with_local_fonts
from general_tools.url_utils import download_file
from urllib.parse import urlsplit, urlunsplit, urlparse
from resource import Resource, Resources, DEFAULT_REF, DEFAULT_OWNER
from rc_link import ResourceContainerLink

DEFAULT_LANG_CODE = 'en'
DEFAULT_ULT_ID = 'ult'
DEFAULT_UST_ID = 'ust'
LANGUAGE_FILES = {
    'en': 'English-en_US.json',
    'fr': 'French-fr_FR.json',
    'kn': 'Kannada-kn_IN.json',
    'shu': 'Chadian_Arabic-shu_CHAD.json'
}
APPENDIX_LINKING_LEVEL = 1
APPENDIX_RESOURCES = ['ta', 'tw']
CONTRIBUTORS_TO_HIDE = ['ugnt', 'uhb']


class PdfConverter:

    def __init__(self, resources: Resources, project_id=None, working_dir=None, output_dir=None,
                 lang_code=DEFAULT_LANG_CODE, regenerate=False, logger=None, offline=False, update=True,
                 *args, **kwargs):
        self.resources = resources
        self.project_id = project_id
        self.working_dir = working_dir
        self.output_dir = output_dir
        self.lang_code = lang_code
        self.regenerate = regenerate
        self.logger = logger
        self.offline = offline
        self.update = not offline and update

        self.logger_handler = None
        self.wp_logger = None
        self.wp_logger_handler = None

        self.save_dir = None
        self.log_dir = None
        self.images_dir = None
        self.output_res_dir = None

        self.errors = {}
        self.bad_highlights = {}
        self.rcs = {}
        self.appendix_rcs = {}
        self.all_rcs = {}

        self.html_file = None
        self.pdf_file = None
        self.docx_file = None
        self.generation_info = {}
        self.translations = {}
        self.remove_working_dir = False
        self.converters_dir = os.path.dirname(os.path.realpath(__file__))
        self.style_sheets = []
        self._font_html = ''

        self._project = None

        self.logger = logger
        self.logger_stream_handler = None

    def __del__(self):
        if self.remove_working_dir:
            shutil.rmtree(self.working_dir)
        if self.logger_handler:
            self.logger.removeHandler(self.logger_handler)
            self.logger_handler.close()
        if self.logger_stream_handler:
            self.logger.removeHandler(self.logger_stream_handler)
            self.logger_stream_handler.close()
        if self.wp_logger_handler:
            self.wp_logger.removeHandler(self.wp_logger_handler)
            self.wp_logger_handler.close()

    @property
    def main_resource(self):
        return self.resources.main

    @property
    def name(self):
        return self.main_resource.resource_name

    @property
    def title(self):
        return self.main_resource.title

    @property
    def simple_title(self):
        return self.main_resource.simple_title

    @property
    def toc_title(self):
        return f'<h1>{self.translate("table_of_contents")}</h1>'

    @property
    def version(self):
        return self.main_resource.version

    @property
    def file_project_and_ref(self):
        return f'{self.file_project_id}_{self.ref}'

    @property
    def file_project_and_unique_ref(self):
        return f'{self.file_project_id}_{self.unique_ref}'

    @property
    def file_ref_id(self):
        return f'{self.file_base_id}_{self.ref}'

    @property
    def file_project_id(self):
        return f'{self.file_base_id}{self.file_id_project_str}'

    @property
    def file_base_id(self):
        return f'{self.lang_code}_{self.name}'

    @property
    def file_id_project_str(self):
        if self.project_id:
            return f'_{self.project_id}'
        else:
            return ''

    @property
    def ref(self):
        if not self.main_resource.ref_is_tag:
            return self.main_resource.ref
        return f'v{self.main_resource.version}'

    @property
    def unique_ref(self):
        if not self.main_resource.ref_is_tag:
            return f'{self.main_resource.ref}_{self.main_resource.commit}'
        return f'v{self.main_resource.version}'

    @property
    def project(self):
        if self.project_id:
            if not self._project:
                self._project = self.main_resource.find_project(self.project_id)
                if not self._project:
                    self.logger.error(f'Project not found: {self.project_id}')
                    exit(1)
            return self._project

    @property
    def project_title(self):
        return self.get_project_title(self.project)

    def get_project_title(self, project):
        if not project:
            project = self.project
        if not project:
            return ''
        if self.main_resource.title in project['title']:
            return project['title'].replace(f' {self.main_resource.title}', '')
        else:
            return project['title'].replace(f' {self.main_resource.simple_title}', '')

    def pad(self, num, project_id=None):
        if not project_id:
            project_id = self.project_id
        if project_id == 'psa':
            return str(num).zfill(3)
        else:
            return str(num).zfill(2)

    @property
    def font_html(self):
        if not self._font_html:
            self._font_html = get_font_html_with_local_fonts(self.lang_code, self.output_dir)
        return self._font_html

    @property
    def language_direction(self):
        if self.main_resource and self.main_resource.language_direction:
            return self.main_resource.language_direction
        else:
            return 'auto'

    @property
    def head_html(self):
        html = f'''{self.font_html}
        <meta name="keywords" content={json.dumps(f'{self.main_resource.identifier},{self.main_resource.type},{self.lang_code},{self.main_resource.language_title},unfoldingWord')} />
        <meta name="author" content={json.dumps(self.main_resource.owner)} />
        <meta name="dcterms.created" content={json.dumps(self.main_resource.issued)} />
'''
        return html

    def add_style_sheet(self, style_sheet):
        if style_sheet not in self.style_sheets:
            self.logger.info(f'Adding CSS style sheet: {style_sheet}')
            self.style_sheets.append(style_sheet)

    def translate(self, key):
        lang = self.lang_code
        if not self.translations:
            if lang not in LANGUAGE_FILES:
                self.logger.error(f'No locale file for {lang}. Using English (en)')
                lang = 'en'
            locale_file = os.path.join(self.converters_dir, 'locale', LANGUAGE_FILES[lang])
            if not os.path.isfile(locale_file):
                self.logger.error(f'No locale file found at {locale_file} for {self.lang_code}.')
                exit(1)
            self.translations = load_json_object(locale_file)
        keys = key.split('.')
        t = self.translations
        for key in keys:
            t = t.get(key, None)
            if t is None:
                # handle the case where the self.translations doesn't have that (sub)key
                self.logger.error(f"No translation for `{key}`")
                exit(1)
                break
        return t

    @staticmethod
    def create_rc(rc_link, article='', title=None, linking_level=0, article_id=None):
        rc = ResourceContainerLink(rc_link, article=article, title=title, linking_level=linking_level,
                                   article_id=article_id)
        return rc

    def add_rc(self, rc_link, article='', title=None, linking_level=0, article_id=None):
        rc = self.create_rc(rc_link, article=article, title=title, linking_level=linking_level, article_id=article_id)
        self.rcs[rc.rc_link] = rc
        return rc

    def add_appendix_rc(self, rc_link, article='', title=None, linking_level=0):
        rc = self.create_rc(rc_link, article=article, title=title, linking_level=linking_level)
        self.appendix_rcs[rc.rc_link] = rc
        return rc

    def add_error_message(self, source_rc, bad_rc_link, message=None):
        if source_rc:
            if source_rc.rc_link not in self.errors:
                self.errors[source_rc.rc_link] = {
                    'source_rc': source_rc,
                    'errors': {}
                }
            if bad_rc_link not in self.errors[source_rc.rc_link] or message:
                self.errors[source_rc.rc_link]['errors'][bad_rc_link] = message

    def add_bad_highlight(self, source_rc, text, rc_link, phrase, message=None):
        if source_rc:
            if source_rc.rc_link not in self.bad_highlights:
                self.bad_highlights[source_rc.rc_link] = {
                    'source_rc': source_rc,
                    'text': text,
                    'highlights': {}
                }
            self.bad_highlights[source_rc.rc_link]['highlights'][rc_link] = {
                'phrase': phrase,
                'fix': message
            }

    def run(self):
        self.setup_working_dir()
        self.setup_resources()
        self.setup_dirs()
        self.setup_style_sheets()
        self.setup_logger()
        self.html_file = os.path.join(self.output_res_dir, f'{self.file_project_and_unique_ref}.html')
        self.pdf_file = os.path.join(self.output_res_dir, f'{self.file_project_and_unique_ref}.pdf')
        self.docx_file = os.path.join(self.output_res_dir, f'{self.file_project_and_unique_ref}.docx')

        self.determine_if_regeneration_needed()
        self.generate_html()
        self.generate_pdf()
        self.finish_up()

    def finish_up(self):
        pass

    def setup_working_dir(self):
        self.logger.info('Setting up working directory...')
        if not self.working_dir:
            if 'WORKING_DIR' in os.environ:
                self.working_dir = os.environ['WORKING_DIR']
                self.logger.info(f'Using env var WORKING_DIR: {self.working_dir}')
            else:
                self.working_dir = tempfile.mkdtemp(prefix=f'{self.main_resource.repo_name}-')
                self.remove_working_dir = True
        self.logger.info(f'Working directory is {self.working_dir}')

    def setup_dirs(self):
        self.logger.info('Setting up directories...')
        if not self.output_dir:
            if 'OUTPUT_DIR' in os.environ:
                self.output_dir = os.environ['OUTPUT_DIR']
                self.logger.info(f'Using env var OUTPUT_DIR: {self.output_dir}')
            if not self.output_dir:
                self.output_dir = self.working_dir
                self.remove_working_dir = False
        self.logger.info(f'Output directory is {self.output_dir}')

        if not os.path.exists(self.working_dir):
            os.makedirs(self.working_dir)

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        self.output_res_dir = os.path.join(self.output_dir, f'{self.name}_{self.ref}')
        if not os.path.exists(self.output_res_dir):
            os.mkdir(self.output_res_dir)
        self.logger.info(f'Resource output directory is {self.output_res_dir}')

        self.images_dir = os.path.join(self.output_dir, 'images')
        if not os.path.exists(self.images_dir):
            os.makedirs(self.images_dir)
        self.logger.info(f'Images directory is {self.images_dir}')
        if self.main_resource.resource_name == 'obs':
            jpg_dir = os.path.join(self.images_dir, 'cdn.door43.org', 'obs', 'jpg')
            if not os.path.exists(jpg_dir):
                download_file('http://cdn.door43.org/obs/jpg/obs-images-360px-compressed.zip',
                              os.path.join(self.images_dir, 'images.zip'))
                unzip(os.path.join(self.images_dir, 'images.zip'), jpg_dir)
                os.unlink(os.path.join(self.images_dir, 'images.zip'))

        self.save_dir = os.path.join(self.output_dir, 'save')
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
        self.logger.info(f'Save directory is {self.save_dir}')

        self.log_dir = os.path.join(self.output_dir, 'log')
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        self.logger.info(f'Log directory is {self.log_dir}')

        css_link = os.path.join(self.output_dir, 'css')
        if not os.path.exists(css_link):
            css_path = os.path.join(self.converters_dir, 'templates/css')
            symlink(css_path, css_link)

        index_link = os.path.join(self.output_dir, 'index.php')
        if not os.path.exists(index_link):
            index_path = os.path.join(self.converters_dir, 'index.php')
            symlink(index_path, index_link)
        self.logger.info(f'index.php file linked to {index_link}')

    def setup_style_sheets(self):
        self.add_style_sheet('../css/style.css')
        possible_styles = [self.lang_code, self.name, self.main_resource.resource_name, f'{self.lang_code}_{self.name}']
        for style in possible_styles:
            style_file = f'../css/{style}_style.css'
            style_path = os.path.join(self.converters_dir, f'templates/css/{style}_style.css')
            if os.path.exists(style_path):
                self.add_style_sheet(style_file)

    def setup_logger(self):
        self.logger.info(f'Setting up logger for {self.file_project_and_unique_ref}')
        self.logger.setLevel(logging.DEBUG)
        log_file = os.path.join(self.log_dir, f'{self.file_project_and_unique_ref}_logger.log')
        self.logger_handler = logging.FileHandler(log_file)
        self.logger.addHandler(self.logger_handler)
        self.logger.info(f'Logging script output to {log_file}')

        link_file_path = os.path.join(self.log_dir, f'{self.file_project_and_ref}_logger_latest.log')
        symlink(log_file, link_file_path, True)

        self.wp_logger = logging.getLogger('weasyprint')
        self.wp_logger.setLevel(logging.DEBUG)
        log_file = os.path.join(self.log_dir, f'{self.file_project_and_unique_ref}_weasyprint.log')
        self.wp_logger_handler = logging.FileHandler(log_file)
        self.wp_logger_handler.setLevel(logging.DEBUG)
        self.wp_logger.addHandler(self.wp_logger_handler)
        self.logger.info(f'Logging WeasyPrint output to {log_file}')

        link_file_path = os.path.join(self.log_dir, f'{self.file_project_and_ref}_weasyprint_latest.log')
        symlink(log_file, link_file_path, True)

    def generate_html(self):
        if self.regenerate or not os.path.exists(self.html_file):
            if os.path.islink(self.html_file):
                os.unlink(self.html_file)

            self.logger.info(f'Creating HTML file for {self.file_project_and_unique_ref}...')

            self.logger.info('Generating cover page HTML...')
            cover_html = self.get_cover_html()

            self.logger.info('Generating license page HTML...')
            license_html = self.get_license_html()

            self.logger.info('Generating body HTML...')
            body_html = self.get_body_html()
            self.logger.info('Generating appendix RCs...')
            self.get_appendix_rcs()
            self.all_rcs = {**self.rcs, **self.appendix_rcs}
            if 'ta' in self.resources:
                self.logger.info('Generating UTA appendix HTML...')
                body_html += self.get_appendix_html(self.resources['ta'])
            if 'tw' in self.resources:
                self.logger.info('Generating UTW appendix HTML...')
                body_html += self.get_appendix_html(self.resources['tw'])
            self.logger.info('Fixing links in body HTML...')
            body_html = self.fix_links(body_html)
            body_html = self._fix_links(body_html)
            write_file('/tmp/text.html', body_html)
            self.logger.info('Replacing RC links in body HTML...')
            body_html = self.replace_rc_links(body_html)
            self.logger.info('Generating Contributors HTML...')
            body_html += self.get_contributors_html()
            self.logger.info('Generating TOC HTML...')
            body_html, toc_html = self.get_toc_html(body_html)
            self.logger.info('Done generating TOC HTML.')

            self.logger.info('Populating HTML template...')
            with open(os.path.join(self.converters_dir, 'templates/template.html')) as template_file:
                html_template = string.Template(template_file.read())
            title = f'{self.title} - v{self.version}'

            self.logger.info('Piecing together the HTML file...')
            body_html = '\n'.join([cover_html, license_html, toc_html, body_html])
            if not self.offline:
                body_html = self.download_all_images(body_html)
            head = '\n'.join([f'<link href="{style}" rel="stylesheet">' for style in self.style_sheets])
            head += self.head_html
            html = html_template.safe_substitute(lang=self.lang_code, dir=self.language_direction, title=title, 
                                                 head=head, body=body_html)
            write_file(self.html_file, html)

            link_file_path = os.path.join(self.output_res_dir, f'{self.file_project_and_ref}_latest.html')
            symlink(self.html_file, link_file_path, True)

            self.save_errors_html()
            self.save_bad_highlights_html()
            self.save_resource_data()
            self.logger.info('Generated HTML file.')
        else:
            self.logger.info(f'HTML file {self.html_file} is already there. Not generating. Use -r to force regeneration.')

    def generate_pdf(self):
        if self.regenerate or not os.path.exists(self.pdf_file):
            self.logger.info(f'Generating PDF file {self.pdf_file}...')
            # Convert HTML to PDF with weasyprint
            base_url = self.output_res_dir
            self.logger.info(f'BASE_URL for PDF is: {base_url}')
            all_pages_fitted = False
            soup = BeautifulSoup(read_file(self.html_file), 'html.parser')
            all_pages_fit = False
            doc = None
            tries = 0
            while not all_pages_fit and tries < 10:
                all_pages_fit = True
                tries += 1
                doc = HTML(string=str(soup), base_url=base_url).render()
                for page_idx, page in enumerate(doc.pages):
                    for anchor in page.anchors:
                        if anchor.startswith('fit-to-page-'):
                            if anchor not in doc.pages[page_idx - 1].anchors:
                                continue
                            all_pages_fit = False
                            diff = 0.05
                            if page.anchors[anchor][1] > 90:
                                diff = 0.1
                            element = soup.find(id=anchor)
                            if not element:
                                continue
                            if element.has_attr('style'):
                                style = parseStyle(element['style'])
                            else:
                                style = CSSStyleDeclaration()
                            if 'font-size' in style and style['font-size'] and style['font-size'].endswith('em'):
                                font_size = float(style['font-size'].removesuffix('em'))
                            else:
                                font_size = 1.0
                            font_size_str = f'{"%.2f" % (font_size - diff)}em'
                            style['font-size'] = font_size_str
                            css = style.cssText
                            element['style'] = css
                            self.logger.info(f'RESIZING {anchor} to {font_size_str}... ({diff}, {page.anchors[anchor]})')
                write_file(os.path.join(self.output_res_dir, f'{self.file_project_and_ref}_resized.html'),
                           str(soup))
            if doc:
                doc.write_pdf(self.pdf_file)
                self.logger.info('Generated PDF file.')
                self.logger.info(f'PDF file located at {self.pdf_file}')
        else:
            self.logger.info(
                f'PDF file {self.pdf_file} is already there. Not generating. Use -r to force regeneration.')

    # def generate_docx(self):
    #     if self.regenerate or not os.path.exists(self.docx_file):
    #         if os.path.islink(self.docx_file):
    #             os.unlink(self.docx_file)
    #         self.logger.info(f'Generating DOCX file {self.docx_file}...')
    #         # Convert HTML to DOCX with pypandoc
    #         pypandoc.convert(source=self.html_file, format='html', to='docx', outputfile=self.docx_file,
    #                          extra_args=['-RTS'])
    #         self.logger.info('Generated DOCX file.')
    #         self.logger.info(f'DOCX file located at {self.pdf_file}')
    #
    #         link_file_path = os.path.join(self.output_res_dir, f'{self.file_project_and_ref}_latest.docx')
    #         symlink(self.docx_file, link_file_path, True)
    #     else:
    #         self.logger.info(
    #             f'DOCX file {self.docx_file} is already there. Not generating. Use -r to force regeneration.')

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
            source_rc = self.errors[source_rc_link]['source_rc']
            errors = self.errors[source_rc_link]['errors']
            for rc_link in sorted(errors.keys()):
                errors_html += f'''
    <li>
        In article 
        <a href="{os.path.basename(self.html_file)}#{source_rc.article_id}" title="See in the HTML" target="{self.name}-html">
            {source_rc_link}
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
        html = html_template.safe_substitute(title=f'ERRORS FOR {self.file_project_and_unique_ref}',
                                             lang='auto', dir='ltr', head=self.head_html,
                                             body=errors_html)
        write_file(save_file, html)
        symlink(save_file, link_file_path, True)

        self.logger.info(f'ERRORS HTML file can be found at {save_file}')

    def save_bad_highlights_html(self):
        save_file = os.path.join(self.output_res_dir, f'{self.file_project_and_unique_ref}_bad_highlights.html')
        link_file_path = os.path.join(self.output_res_dir, f'{self.file_project_and_ref}_bad_highlights_latest.html')

        if not self.bad_highlights:
            self.logger.info('No bad highlights for this version!')
            if os.path.exists(save_file):
                os.unlink(save_file)
            if os.path.exists(link_file_path):
                os.unlink(link_file_path)
            return

        bad_highlights_html = f'''
<h1>BAD HIGHLIGHTS:</h1>
<h2>(i.e. phrases not found in text as written)</h2>
<ul>
'''
        for source_rc_link in sorted(self.bad_highlights.keys()):
            source_rc = self.bad_highlights[source_rc_link]['source_rc']
            bad_highlights_html += f'''
    <li>
        <a href="{os.path.basename(self.html_file)}#{source_rc.article_id}" title="See in the HTML" target="{self.name}-html">
            {source_rc.rc_link}
        </a>:
        <br/>
        {self.bad_highlights[source_rc_link]['text']}
        <br/>
        <ul>
'''
            for target_rc_link in self.bad_highlights[source_rc_link]['highlights'].keys():
                target = self.bad_highlights[source_rc_link]['highlights'][target_rc_link]
                bad_highlights_html += f'''
            <li>
                {target_rc_link}: {target['phrase']} <em>(phrase to match)</em>
'''
                if target['fix']:
                    bad_highlights_html += f'''
                <br/>
                {target['fix']} <em>(QUOTE ISSUE - closest phrase found in text)</em>
'''
                bad_highlights_html += f'''
            </li>
'''
            bad_highlights_html += '''
        </ul>
    </li>'''
        bad_highlights_html += '''
</ul>
'''
        with open(os.path.join(self.converters_dir, 'templates/template.html')) as template_file:
            html_template = string.Template(template_file.read())
        html = html_template.safe_substitute(title=f'BAD HIGHLIGHTS FOR {self.file_project_and_unique_ref}',
                                             lang='auto', dir='ltr', head=self.head_html,
                                             body=bad_highlights_html)
        write_file(save_file, html)
        symlink(save_file, link_file_path, True)

        self.logger.info(f'BAD HIGHLIGHTS file can be found at {save_file}')

    def setup_resource(self, resource):
        self.logger.info(f'Setting up resource {resource.resource_name}...')
        resource.update = self.update
        resource.clone(self.working_dir)
        self.logger.info(f'  ...set up to use `{resource.repo_name}`: `{resource.ref}` ({resource.commit})')
        self.generation_info[resource.repo_name] = {'ref': resource.ref, 'commit': resource.commit}
        #logo_path = os.path.join(self.images_dir, resource.logo_file)
        #if not os.path.exists(logo_path) and not self.offline:
        #    try:
        #        download_file(resource.logo_url, logo_path)
        #    except IOError:
        #        self.logger.error(f'No logo file found for {resource.logo_url}')

    def setup_resources(self):
        self.logger.info('Setting up resources...')
        for resource_name, resource in self.resources.items():
            self.setup_resource(resource)

    def determine_if_regeneration_needed(self):
        # check if any commit hashes have changed
        old_info = self.get_previous_generation_info()
        for repo_name in self.generation_info:
            new_commits = False
            if not self.regenerate and old_info and repo_name in old_info and repo_name in self.generation_info:
                old_ref = old_info[repo_name]['ref']
                new_ref = self.generation_info[repo_name]['ref']
                old_commit = old_info[repo_name]['commit']
                new_commit = self.generation_info[repo_name]['commit']
                if old_ref != new_ref or old_commit != new_commit:
                    self.logger.info(f'Resource {repo_name} has changed: {old_ref} => {new_ref}, {old_commit} => {new_commit}. REGENERATING PDF.')
                    new_commits = True
                    self.regenerate = True
            else:
                if not self.regenerate:
                    self.logger.info(f'Looks like this the first run for {self.file_project_and_unique_ref}.')
                new_commits = True
                self.regenerate = True
            if new_commits:
                self.resources[self.main_resource.resource_name].new_commits = True

    def save_resource_data(self):
        save_file = os.path.join(self.save_dir, f'{self.file_project_and_unique_ref}_rcs.json')
        write_file(save_file, jsonpickle.dumps(self.rcs))
        link_file_path = os.path.join(self.save_dir, f'{self.file_project_and_ref}_rcs_latest.json')
        symlink(save_file, link_file_path, True)

        save_file = os.path.join(self.save_dir, f'{self.file_project_and_unique_ref}_appendix_rcs.json')
        write_file(save_file, jsonpickle.dumps(self.appendix_rcs))
        link_file_path = os.path.join(self.save_dir, f'{self.file_project_and_ref}_appendix_rcs_latest.json')
        symlink(save_file, link_file_path, True)

        save_file = os.path.join(self.save_dir, f'{self.file_project_and_unique_ref}_errors.json')
        write_file(save_file, jsonpickle.dumps(self.errors))
        link_file_path = os.path.join(self.save_dir, f'{self.file_project_and_ref}_errors_latest.json')
        symlink(save_file, link_file_path, True)

        save_file = os.path.join(self.save_dir, f'{self.file_project_and_unique_ref}_bad_highlights.json')
        write_file(save_file, jsonpickle.dumps(self.bad_highlights))
        link_file_path = os.path.join(self.save_dir, f'{self.file_project_and_ref}_bad_highlights_latest.json')
        symlink(save_file, link_file_path, True)

        save_file = os.path.join(self.save_dir, f'{self.file_project_and_ref}_generation_info.json')
        write_file(save_file, jsonpickle.dumps(self.generation_info))

    def get_previous_generation_info(self):
        save_file = os.path.join(self.save_dir, f'{self.file_project_and_ref}_generation_info.json')
        if os.path.isfile(save_file):
            return load_json_object(save_file)
        else:
            return {}

    def download_all_images(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        for img in soup.find_all('img'):
            if img['src'].startswith('http'):
                u = urlsplit(img['src'])._replace(query="", fragment="")
                url = urlunsplit(u)
                file_path = f'images/{u.netloc}{u.path}'
                full_file_path = os.path.join(self.output_dir, file_path)
                if not os.path.exists(full_file_path) and not self.offline and all(ord(c) < 128 for c in url):
                    os.makedirs(os.path.dirname(full_file_path), exist_ok=True)
                    self.logger.info(f'Downloading {url} to {full_file_path}...')
                    download_file(url, full_file_path)
                img['src'] = f'../{file_path}'
        return str(soup)

    @abstractmethod
    def get_body_html(self):
        pass

    def get_rc_by_article_id(self, article_id):
        for rc_link, rc in self.all_rcs.items():
            if rc.article_id == article_id:
                return rc

    def get_toc_html(self, body_html):
        toc_html = f'''
<article id="contents">
    {self.toc_title}
'''
        prev_toc_level = 0
        prev_header_level = 0
        soup = BeautifulSoup(body_html, 'html.parser')
        header_titles = [None, None, None, None, None, None]
        headers = soup.find_all(re.compile(r'^h\d'), {'class': 'section-header'})
        for header in headers:
            if header.get('id'):
                article_id = header.get('id')
            else:
                parent = header.find_parent(['article', 'section'])
                article_id = parent.get('id')

            if article_id:
                is_toc = not header.has_attr('class') or 'no-toc' not in header['class']
                is_header = not header.has_attr('class') or 'no-header' not in header['class']

                if not is_toc and not is_header:
                    continue

                toc_level = int(header.get('toc-level', header.name[1]))
                header_level = int(header.get('header-level', toc_level))

                # Get the proper TOC title and add it to the TOC string with an open <li>
                if is_toc:
                    if toc_level > prev_toc_level:
                        for level in range(prev_toc_level, toc_level):
                            toc_html += '\n<ul>\n'
                    elif toc_level < prev_toc_level:
                        toc_html += '\n</li>\n'  # close current item's open <li> tag
                        for level in range(prev_toc_level, toc_level, -1):
                            toc_html += '</ul>\n</li>\n'
                    elif prev_toc_level > 0:
                        toc_html += '\n</li>\n'

                    if header.has_attr('toc_title'):
                        toc_title = header['toc_title']
                    else:
                        rc = self.get_rc_by_article_id(article_id)
                        if rc:
                            toc_title = rc.toc_title
                        else:
                            toc_title = header.text
                    toc_html += f'<li><a href="#{article_id}"><span>{toc_title}</span></a>\n'
                    prev_toc_level = toc_level

                # Get the proper Heading title and add a header tag
                if is_header:
                    if header_level > prev_header_level:
                        for level in range(prev_header_level, header_level):
                            header_titles[level] = None
                    elif header_level < prev_header_level:
                        for level in range(prev_header_level, header_level, -1):
                            header_titles[level - 1] = None

                    if header.has_attr('header_title'):
                        header_title = header['header_title']
                    else:
                        rc = self.get_rc_by_article_id(article_id)
                        if rc:
                            header_title = rc.toc_title
                        else:
                            header_title = header.text
                    header_titles[header_level - 1] = header_title

                    right_header_string = ' :: '.join(filter(None, header_titles[1:header_level]))
                    if len(right_header_string):
                        right_header_tag = soup.new_tag('span', **{'class': 'hidden header-right'})
                        right_header_tag.string = right_header_string
                        header.insert_before(right_header_tag)
                    prev_header_level = header_level

        for level in range(prev_toc_level, 0, -1):
            toc_html += '</li>\n</ul>\n'
        toc_html += '</article>'

        return [str(soup), toc_html]

    def get_cover_html(self):
        version_str = f'{self.translate("license.version")} {self.version}'
        if self.main_resource.ref == DEFAULT_REF:
           version_str += f' ({DEFAULT_REF} - {self.main_resource.commit})'
        if self.project_id:
            project_title_html = f'<h2 class="cover-project">{self.project_title}</h2>'
            version_title_html = f'<h3 class="cover-version">{version_str}</h3>'
        else:
            project_title_html = ''
            version_title_html = f'<h2 class="cover-version">{version_str}</h2>'
        cover_html = f'''
<article id="main-cover" class="cover">
    <img src="{self.main_resource.logo_url}" alt="{self.name.upper()}"/>
    <h1 id="cover-title">{self.title}</h1>
    {project_title_html}
    {version_title_html}
</article>
'''
        return cover_html

    def get_license_html(self):
        license_html = f'''
<article id="copyrights-and-license">
    <div id="copyrights">
        <h1>{self.translate('license.copyrights_and_licensing')}</h1>
'''
        for resource_name, resource in self.resources.items():
            if resource.background_resource or not resource.manifest:
                continue
            title = resource.title
            version = resource.version
            publisher = resource.publisher
            issued = resource.issued

            version_str = version
            if resource.ref == DEFAULT_REF:
                version_str += f' ({DEFAULT_REF} - {resource.commit})'
                issued = f'{resource.commit_date} (last commit)'
              
            license_html += f'''
        <div class="resource-info">
          <div class="resource-title"><strong>{title}</strong></div>
          <div class="resource-date"><strong>{self.translate('license.date')}:</strong> {issued}</div>
          <div class="resource-version"><strong>{self.translate('license.version')}:</strong> {version_str}</div>
          <div class="resource-publisher"><strong>{self.translate('license.published_by')}:</strong> {publisher}</div>
        </div>
    </div>
    <div id="license">
'''
        license_file = os.path.join(self.main_resource.repo_dir, 'LICENSE.md')
        license_html += markdown2.markdown_path(license_file)
        license_html += '''
    </div>
</article>
'''
        return license_html

    def get_contributors_html(self):
        contributors_html = '''
<section id="contributors" class="no-header">
'''
        for idx, resource_name \
                in enumerate(self.resources.keys()):
            resource = self.resources[resource_name]
            if resource.background_resource or not resource.manifest or not resource.contributors or \
                    resource_name in CONTRIBUTORS_TO_HIDE:
                continue
            contributors = resource.contributors
            contributors_list_classes = 'contributors-list'
            if len(contributors) > 10:
                contributors_list_classes += ' more-than-ten'
            elif len(contributors) > 4:
                contributors_list_classes += ' more-than-four'
            contributors_html += f'<div class="{contributors_list_classes}">'
            if idx == 0:
                contributors_html += f'<h1 class="section-header">{self.translate("contributors")}</h1>'
            if len(self.resources) > 1:
                contributors_html += f'<h2 id="{self.lang_code}-{resource_name}-contributors" class="section-header">{resource.title} {self.translate("contributors")}</h2>'
            for contributor in contributors:
                contributors_html += f'<div class="contributor">{contributor}</div>'
            contributors_html += '</div>'
        contributors_html += '''
</section>
'''
        return contributors_html

    def replace(self, m):
        before = m.group(1)
        rc_link = m.group(2)
        after = m.group(3)
        if rc_link not in self.all_rcs:
            return m.group()
        rc = self.all_rcs[rc_link]
        if (before == '[[' and after == ']]') or (before == '(' and after == ')') or before == ' ' \
                or (before == '>' and after == '<'):
            return f'<a href="#{rc.article_id}">{rc.title}</a>'
        if (before == '"' and after == '"') or (before == "'" and after == "'"):
            return f'#{rc.article_id}'
        self.logger.error(f'FOUND SOME MALFORMED RC LINKS: {m.group()}')
        return m.group()

    def replace_rc_links(self, text):
        soup = BeautifulSoup(text, 'html.parser')
        rc_pattern = 'rc://[/A-Za-z0-9*_-]+'
        rc_regex = re.compile(rc_pattern)

        # Find anchor tags with an href of an rc link
        anchors_with_rc = soup.find_all('a', href=rc_regex)
        for anchor in anchors_with_rc:
            href_rc_link = anchor['href']
            if href_rc_link in self.all_rcs and self.all_rcs[href_rc_link].linking_level <= APPENDIX_LINKING_LEVEL:
                href_rc = self.all_rcs[href_rc_link]
                anchor['href'] = f'#{href_rc.article_id}'
            else:
                anchor.replace_with_children()

        # Find text either [[rc://...]] links or rc://... links and make them anchor elements
        text_with_bracketed_rcs = soup(text=rc_regex)
        for element_text in text_with_bracketed_rcs:
            parts = re.split(rf'(\[*{rc_pattern}\]*)', element_text)
            last_part = soup.new_string(parts[0])
            element_text.replace_with(last_part)
            for part in parts[1:]:
                if not re.search(rc_regex, part):
                    part = soup.new_string(part)
                else:
                    rc_link = part.strip('[]')
                    if rc_link in self.all_rcs and self.all_rcs[rc_link].linking_level <= APPENDIX_LINKING_LEVEL:
                        part = BeautifulSoup(f'<a href="#{self.all_rcs[rc_link].article_id}">{self.all_rcs[rc_link].title}</a>',
                                             'html.parser').find('a')
                    else:
                        part = soup.new_string(part)
                last_part.insert_after(part)
                last_part = part

        return str(soup)

    @staticmethod
    def _fix_links(html):
        # Change [[http.*]] to <a href="http\1">http\1</a>
        html = re.sub(r'\[\[http([^\]]+)\]\]', r'<a href="http\1">http\1</a>', html, flags=re.IGNORECASE)

        # convert URLs to links if not already
        html = re.sub(r'([^">])((http|https|ftp)://[A-Za-z0-9/?&_.:=#-]+[A-Za-z0-9/?&_:=#-])',
                      r'\1<a href="\2">\2</a>', html, flags=re.IGNORECASE)

        # URLS wth just www at the start, no http
        html = re.sub(r'([^/])(www\.[A-Za-z0-9/?&_.:=#-]+[A-Za-z0-9/?&_:=#-])', r'\1<a href="http://\2">\2</a>',
                      html, flags=re.IGNORECASE)

        return html

    def fix_links(self, html):
        # can be implemented by child class
        return html

    def get_appendix_rcs(self):
        for rc_link, rc in self.rcs.items():
            self.crawl_ta_tw_deep_linking(rc)

    def crawl_ta_tw_deep_linking(self, source_rc: ResourceContainerLink):
        if not source_rc or not source_rc.article:
            return
        self.logger.info(f'Crawling {source_rc.rc_link} (level: {source_rc.linking_level})...')
        # get all rc links. the "?:" in the regex means to not leave the (ta|tw) match in the result
        rc_links = re.findall(r'rc://[A-Z0-9_*-]+/(?:ta|tw)/[A-Z0-9/_*-]+', source_rc.article, flags=re.IGNORECASE | re.MULTILINE)
        for rc_link in rc_links:
            if rc_link in self.rcs or rc_link in self.appendix_rcs:
                rc = self.rcs[rc_link] if rc_link in self.rcs else self.appendix_rcs[rc_link]
                if rc.linking_level > source_rc.linking_level + 1:
                    rc.linking_level = source_rc.linking_level + 1
                already_crawled = True
            else:
                rc = self.add_appendix_rc(rc_link, linking_level=source_rc.linking_level + 1)
                if rc.resource not in self.resources:
                    # We don't have this resource in our list of resources, so adding
                    resource = Resource(resource_name=rc.resource, repo_name=f'{self.lang_code}_{rc.resource}',
                                        owner=self.main_resource.owner)
                    self.setup_resource(resource)
                already_crawled = False
            rc.add_reference(source_rc)
            if not rc.article and (not already_crawled or rc.linking_level <= APPENDIX_LINKING_LEVEL):
                if rc.resource == 'ta':
                    self.get_ta_article_html(rc, source_rc)
                elif rc.resource == 'tw':
                    self.get_tw_article_html(rc, source_rc)
                if rc.article and rc.title:
                    if rc.linking_level <= APPENDIX_LINKING_LEVEL:
                        self.crawl_ta_tw_deep_linking(rc)
                    else:
                        rc.set_article(None)
                else:
                    self.add_error_message(source_rc, rc.rc_link)
                    self.logger.error(f'LINK TO UNKNOWN RESOURCE FOUND IN {source_rc.rc_link}: {rc.rc_link}')
                    del self.appendix_rcs[rc.rc_link]

    def get_appendix_html(self, resource):
        html = ''
        filtered_rcs = dict(filter(lambda x: x[1].resource == resource.resource_name and
                                   x[1].linking_level == APPENDIX_LINKING_LEVEL,
                            self.appendix_rcs.items()))
        sorted_rcs = sorted(filtered_rcs.items(), key=lambda x: x[1].title.lower())
        for item in sorted_rcs:
            rc = item[1]
            if rc.article:
                html += rc.article.replace('</article>', self.get_go_back_to_html(rc) + '</article>')
        if html:
            html = f'''
<section>
    <article id="{self.lang_code}-{resource.resource_name}-appendix-cover" class="resource-title-page break">
        <img src="{resource.logo_url}" alt="{resource.resource_name.upper()}">
        <h1 class="section-header">{resource.title}</h1>
        <h2 class="cover-version">{self.translate("license.version")} {resource.version}</h2>
    </article>
    {html}
</section>
'''
        return html

    def get_ta_article_html(self, rc, source_rc, config=None, toc_level=2):
        if not config:
            config_file = os.path.join(self.resources[rc.resource].repo_dir, rc.project, 'config.yaml')
            config = yaml.full_load(read_file(config_file))
        article_dir = os.path.join(self.resources[rc.resource].repo_dir, rc.project, rc.path)
        article_file = os.path.join(article_dir, '01.md')
        if os.path.isfile(article_file):
            article_file_html = markdown2.markdown_path(article_file, extras=['markdown-in-html', 'tables', 'break-on-newline'])
        else:
            message = 'no corresponding article found'
            if os.path.isdir(article_dir):
                if not os.path.isfile(article_file):
                    message = 'dir exists but no 01.md file'
                else:
                    message = '01.md file exists but no content'
            self.add_error_message(source_rc, rc.rc_link, message)
            self.logger.error(f'TA ARTICLE NOT FOUND: {article_file} - {message}')
            return
        top_box = ''
        bottom_box = ''
        question = ''
        dependencies = ''
        recommendations = ''

        title = rc.title
        if not title:
            title_file = os.path.join(article_dir, 'title.md')
            title = read_file(title_file)
            rc.set_title(title)

        question_file = os.path.join(article_dir, 'sub-title.md')
        if os.path.isfile(question_file):
            question = f'''
        <div class="ta-question">
            {self.translate('this_page_answers_the_question')}: <em>{read_file(question_file)}<em>
        </div>
'''
        if rc.path in config:
            if 'dependencies' in config[rc.path] and config[rc.path]['dependencies']:
                lis = ''
                for dependency in config[rc.path]['dependencies']:
                    dep_project = rc.project
                    for project in self.resources['ta'].projects:
                        dep_article_dir = os.path.join(self.resources['ta'].repo_dir, project['identifier'], dependency)
                        if os.path.isdir(dep_article_dir):
                            dep_project = project['identifier']
                    dep_rc_link = f'rc://{self.lang_code}/ta/man/{dep_project}/{dependency}'
                    lis += f'''
                    <li>[[{dep_rc_link}]]</li>
'''
                dependencies += f'''
        <div class="ta-dependencies">
            {self.translate('in_order_to_understand_this_topic')}:
            <ul>
                {lis}
            </ul>
        </div>
'''
            if 'recommended' in config[rc.path] and config[rc.path]['recommended']:
                lis = ''
                for recommended in config[rc.path]['recommended']:
                    rec_project = rc.project
                    rec_article_dir = os.path.join(self.resources['ta'].repo_dir, rec_project, recommended)
                    if not os.path.exists(rec_article_dir):
                        for project in self.resources['ta'].projects:
                            rec_article_dir = os.path.join(self.resources['ta'].repo_dir, project['identifier'], recommended)
                            if os.path.isdir(rec_article_dir):
                                rec_project = project['identifier']
                                break
                    if not os.path.exists(rec_article_dir):
                        bad_rc_link = f"{rc.project}/config.yaml -> '{rc.path}' -> 'recommended' -> '{recommended}'"
                        self.add_error_message(rc, bad_rc_link)
                        self.logger.error(f'RECOMMENDED NOT FOUND FOR {bad_rc_link}')
                        continue
                    rec_rc_link = f'rc://{self.lang_code}/ta/man/{rec_project}/{recommended}'
                    lis += f'''
                    <li>[[{rec_rc_link}]]</li>
'''
                recommendations = f'''
            <div class="ta-recommendations">
                {self.translate('next_we_recommend_you_learn_about')}:
                <ul>
                    {lis}
                </ul>
            </div>
'''

        if question or dependencies:
            top_box = f'''
    <div class="top-box box">
        {question}
        {dependencies}
    </div>
'''
        if recommendations:
            bottom_box = f'''
    <div class="bottom-box box">
        {recommendations}
    </div>
'''
        article_html = f'''
<article id="{rc.article_id}">
    <h{toc_level} class="section-header" toc-level="{toc_level}">{rc.title}</h{toc_level}>
    {top_box}
    {article_file_html}
    {bottom_box}
</article>'''
        article_html = self.fix_ta_links(article_html, rc.project)
        rc.set_article(article_html)

    def get_go_back_to_html(self, source_rc):
        if source_rc.linking_level == 0:
            return ''
        go_back_tos = []
        for rc_link in source_rc.references:
            if rc_link in self.rcs:
                rc = self.rcs[rc_link]
                go_back_tos.append(f'<a href="#{rc.article_id}">{rc.title}</a>')
        go_back_to_html = ''
        if len(go_back_tos):
            go_back_tos_string = '; '.join(go_back_tos)
            go_back_to_html = f'''
    <div class="go-back-to">
        (<strong>{self.translate('go_back_to')}:</strong> {go_back_tos_string})
    </div>
'''
        return go_back_to_html

    def fix_ta_links(self, text, project):
        text = re.sub(r'href="\.\./\.\./([^/"]+)/([^/"]+?)/*(01\.md)*"', rf'href="rc://{self.lang_code}/ta/man/\1/\2"', text,
                      flags=re.IGNORECASE | re.MULTILINE)
        text = re.sub(r'href="\.\./([^/"]+?)/*(01\.md)*"', rf'href="rc://{self.lang_code}/ta/man/{project}/\1"', text,
                      flags=re.IGNORECASE | re.MULTILINE)
        text = re.sub(r'href="([^# :/"]+)"', rf'href="rc://{self.lang_code}/ta/man/{project}/\1"', text,
                      flags=re.IGNORECASE | re.MULTILINE)
        return text

    def get_tw_article_html(self, rc, source_rc=None, increment_header_depth=1):
        file_path = os.path.join(self.resources[rc.resource].repo_dir, rc.project, f'{rc.path}.md')
        fix = None
        if not os.path.exists(file_path):
            bad_names = {
                'live': 'bible/kt/life'
            }
            if rc.extra_info[-1] in bad_names:
                path2 = bad_names[rc.extra_info[-1]]
            elif rc.path.startswith('bible/other/'):
                path2 = re.sub(r'^bible/other/', r'bible/kt/', rc.path)
            else:
                path2 = re.sub(r'^bible/kt/', r'bible/other/', rc.path)
            fix = 'change to rc://{0}/tw/dict/{1}'.format(self.lang_code, path2)
            file_path = os.path.join(self.resources[rc.resource].repo_dir, rc.project, f'{path2}.md')
        if os.path.isfile(file_path):
            if fix:
                self.add_error_message(source_rc, rc.rc_link, fix)
                self.logger.error(f'FIX FOUND FOR FOR TW ARTICLE IN {source_rc.rc_link}: {rc.rc_link} => {fix}')
            tw_article_html = markdown2.markdown_path(file_path)
            tw_article_html = html_tools.make_first_header_section_header(tw_article_html)
            tw_article_html = html_tools.increment_headers(tw_article_html, increment_header_depth)
            tw_article_html = self.fix_tw_links(tw_article_html, rc.extra_info[0])
            tw_article_html = f'''                
<article id="{rc.article_id}">
    {tw_article_html}
</article>
'''
            rc.set_title(html_tools.get_title_from_html(tw_article_html))
            rc.set_article(tw_article_html)
        else:
            self.add_error_message(source_rc, rc.rc_link)
            self.logger.error(f'TW ARTICLE NOT FOUND: {file_path}')

    def fix_tw_links(self, text, group):
        text = re.sub(r'href="\.\./([^/)]+?)(\.md)*"', rf'href="rc://{self.lang_code}/tw/dict/bible/{group}/\1"', text,
                      flags=re.IGNORECASE | re.MULTILINE)
        text = re.sub(r'href="\.\./([^)]+?)(\.md)*"', rf'href="rc://{self.lang_code}/tw/dict/bible/\1"', text,
                      flags=re.IGNORECASE | re.MULTILINE)
        text = re.sub(r'(\(|\[\[)(\.\./)*(kt|names|other)/([^)]+?)(\.md)*(\)|\]\])(?!\[)',
                      rf'[[rc://{self.lang_code}/tw/dict/bible/\3/\4]]', text,
                      flags=re.IGNORECASE | re.MULTILINE)
        return text


def run_converter(resource_names: List[str], pdf_converter_class: Type[PdfConverter], logo_url=None,
                  project_ids_map=None, parser=None, extra_resource_ids=None):
    if not parser:
        parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-r', '--regenerate', dest='regenerate', action='store_true',
                        help='Regenerate PDF even if exists.')
    parser.add_argument('-l', '--lang_code', metavar='LANG', dest='lang_codes', required=False, action='append',
                        help='Language Code. Can specify multiple -l\'s, e.g. -l en -l fr. Default: en')
    parser.add_argument('-p', '--project_id', metavar='PROJECT ID', dest='project_ids', required=False, action='append',
                        help='Project ID for resources with projects, such as a Bible book (-p gen). Can specify multiple -p\'s. Default: None (different converters will handle no or multiple projects differently, such as compiling all into one PDF, or running for each project.)')
    parser.add_argument('-w', '--working', dest='working_dir',  required=False,
                        help='Working directory where multiple repos can be cloned into. Default: a temp directory that gets removed on exit')
    parser.add_argument('-o', '--output', dest='output_dir', required=False,
                        help='Output directory. Will make a subdirectory with the resource name, e.g. `<output_dir>/obs` or `<output_dir>/tn`. Default: <current directory>')
    parser.add_argument('--owner', dest='owner', default=DEFAULT_OWNER, required=False,
                        help=f'Owner of the resource repo on GitHub. Default: {DEFAULT_OWNER}')
    parser.add_argument('--repo', dest='repo', required=False,
                        help=f'Repo name. If not provided, assumes <lang>_<resource>')
    parser.add_argument('-m', '--master', dest='master', action='store_true',
                        help='If resource ref not specified, will use master branch instead of latest tag')
    parser.add_argument('--offline', dest='offline', action='store_true',
                        help='Do not download repos and images or attempt to update them. Will fail if they do not already exist in the working dir.')
    for resource_name in resource_names:
        param_name = resource_name.replace('_', '-')
        parser.add_argument(f'--{param_name}-ref', metavar='TAG|BRANCH', dest=f'{resource_name}_ref', default=None, required=False,
                            help=f'Tag or branch for `{resource_name}`. If not set, uses latest tag, unless --master flag is used')

    args = parser.parse_args(sys.argv[1:])

    lang_codes = args.lang_codes
    owner = args.owner
    repo = args.repo
    offline = args.offline
    master = args.master

    orig_names = {}
    if extra_resource_ids:
      for extra_resource_id in extra_resource_ids:
        orig_name = extra_resource_id.split('_')[0].split('-')[0]
        if hasattr(args, extra_resource_id):
           resource_names.remove(orig_name)
           resource_names += [getattr(args, extra_resource_id)]
           orig_names[getattr(args, extra_resource_id)] =  orig_name
    if not lang_codes:
        lang_codes = [DEFAULT_LANG_CODE]
    project_ids = args.project_ids
    if not project_ids or 'all' in project_ids[0]:
        project_id = '' if not project_ids else project_ids[0]
        if project_ids_map and project_id in project_ids_map:
            project_ids = project_ids_map[project_id]
        elif not project_ids:
            project_ids = [None]

    logger = logging.getLogger(resource_names[0])
    logger.setLevel(logging.DEBUG)
    logger_stream_handler = logging.StreamHandler()
    logger_stream_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(levelname)s - %(message)s")
    logger_stream_handler.setFormatter(formatter)
    logger.addHandler(logger_stream_handler)

    converter_args = vars(args)
    converter_args['logger'] = logger

    print(resource_names)
    for lang_code in lang_codes:
        resources = Resources()
        update = not offline
        for resource_name in resource_names:
            if not repo:
                repo_name = f'{lang_code}_{resource_name}'
            else:
                repo_name = repo
            if resource_name in orig_names:
                ref = getattr(args, f'{orig_names[resource_name]}_ref')
            else:
                ref = getattr(args, f'{resource_name}_ref')
            if not ref and master:
                ref = DEFAULT_REF
            logo = None
            if logo_url and resource_name == resource_names[0]:
                logo = logo_url
            resource = Resource(resource_name=resource_name, repo_name=repo_name, ref=ref, owner=owner, logo_url=logo, offline=offline, update=update)
            resources[resource_name] = resource
        converter_args['lang_code'] = lang_code
        converter_args['resources'] = resources
        for project_id in project_ids:
            converter_args['project_id'] = project_id
            converter_args['update'] = update
            converter = pdf_converter_class(**converter_args)
            project_id_str = f'_{project_id}' if project_id else ''
            logger.info(f'Starting PDF Converter for {converter.name}_{converter.main_resource.ref}{project_id_str}...')
            converter.run()
            update = False
    logger.removeHandler(logger_stream_handler)
    logger_stream_handler.close()


def RepresentsInt(s):
    try:
        int(s)
        return True
    except ValueError:
        return False
