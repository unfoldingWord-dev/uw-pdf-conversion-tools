#!/usr/bin/env python3
#
#  Copyright (c) 2020 unfoldingWord
#  http://creativecommons.org/licenses/MIT/
#  See LICENSE file for details.
#
#  Contributors:
#  Richard Mahn <rich.mahn@unfoldingword.org>

"""
This script generates the TN Note checking PDF
"""
from tn_pdf_converter import TnPdfConverter, main


class TnNoteCheckingPdfConverter(TnPdfConverter):

    @property
    def name(self):
        return 'tn-note-checking'

    def title(self):
        return super().title + ' Checking - Notes'

    def get_tn_chunk_article(self, chapter_chunk_data, chapter, first_verse):
        last_verse = chapter_chunk_data[first_verse]['last_verse']
        chunk_notes = chapter_chunk_data[first_verse]['chunk_notes']
        tn_title = f'{self.project_title} {chapter}:{first_verse}'
        if first_verse != last_verse:
            tn_title += f'-{last_verse}'
        tn_title += ' - NOTES'
        tn_chunk_rc_link = f'rc://{self.lang_code}/tn/help/{self.project_id}/{self.pad(chapter)}/{str(first_verse).zfill(3)}/{str(last_verse).zfill(3)}'
        tn_chunk_rc = self.add_rc(tn_chunk_rc_link, title=tn_title)
        # make an RC for all the verses in this chunk in case they are reference
        for verse in range(first_verse, last_verse + 1):
            verse_rc_link = f'rc://{self.lang_code}/tn/help/{self.project_id}/{self.pad(chapter)}/{str(verse).zfill(3)}'
            self.add_rc(verse_rc_link, title=tn_title, article_id=tn_chunk_rc.article_id)
            self.verse_to_chunk[self.pad(chapter)][str(verse).zfill(3)] = tn_title
        ult_with_tn_quotes = self.get_ult_with_tn_quotes(tn_chunk_rc, int(chapter), first_verse, last_verse)

        ust_scripture = self.get_plain_scripture(self.ust_id, int(chapter), first_verse, last_verse)
        if not ust_scripture:
            ust_scripture = '&nbsp;'
        scripture = f'''
                            <h3 class="bible-resource-title">{self.ult_id.upper()}</h3>
                            <div class="bible-text">{ult_with_tn_quotes}</div>
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


if __name__ == '__main__':
    main(TnNoteCheckingPdfConverter)
