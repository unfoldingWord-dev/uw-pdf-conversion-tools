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
from tn_pdf_converter import TnPdfConverter, main


class TnWordCheckingPdfConverter(TnPdfConverter):

    @property
    def name(self):
        return 'tn-word-checking'

    def title(self):
        return self.main_resource.title + ' Checking - Words'

    def get_tn_chunk_article(self, chapter_chunk_data, chapter, first_verse):
        last_verse = chapter_chunk_data[first_verse]['last_verse']
        chunk_words = chapter_chunk_data[first_verse]['chunk_words']
        tn_title = f'{self.project_title} {chapter}:{first_verse}'
        if first_verse != last_verse:
            tn_title += f'-{last_verse}'
        tn_title += ' - WORDS'
        tn_chunk_rc_link = f'rc://{self.lang_code}/tn/help/{self.project_id}/{self.pad(chapter)}/{str(first_verse).zfill(3)}/{str(last_verse).zfill(3)}/tw'
        tn_chunk_rc = self.add_rc(tn_chunk_rc_link, title=tn_title)
        ult_with_tw_words = self.get_ult_with_tw_words(tn_chunk_rc, int(chapter), first_verse, last_verse)

        ust_scripture = self.get_plain_scripture(self.ust_id, int(chapter), first_verse, last_verse)
        if not ust_scripture:
            ust_scripture = '&nbsp;'
        scripture = f'''
                    <h3 class="bible-resource-title">{self.ult_id.upper()}</h3>
                    <div class="bible-text">{ult_with_tw_words}</div>
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
                                {chunk_words}
                            </div>
                    </div>
                </article>
'''
        tn_chunk_rc.set_article(chunk_article)
        return chunk_article


if __name__ == '__main__':
    main(TnWordCheckingPdfConverter)
