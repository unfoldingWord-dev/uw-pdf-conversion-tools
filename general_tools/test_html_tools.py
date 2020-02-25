from unittest import TestCase
from .html_tools import mark_phrases_in_html, unnest_a_links


class Test(TestCase):
    def test_mark_phrase_in_html(self):
        marked_text = mark_phrases_in_html('here I am', 'I')
        expected_text = 'here <span class="highlight">I</span> am'
        self.assertEqual(expected_text, marked_text)
        marked_text = mark_phrases_in_html('here I now am', 'I...am')
        expected_text = 'here I now <span class="highlight">am</span>'
        self.assertEqual(expected_text, marked_text)
        marked_text = mark_phrases_in_html('here I now am', 'I...am', ignore_small_words=False)
        expected_text = 'here <span class="highlight">I</span> now <span class="highlight">am</span>'
        self.assertEqual(expected_text, marked_text)
        marked_text = mark_phrases_in_html('to be or not to be that is the question', 'to be', occurrence=2)
        expected_text = 'to be or not <span class="highlight">to be</span> that is the question'
        self.assertEqual(expected_text, marked_text)
        marked_text = mark_phrases_in_html('a b c a b c a b c a b c a b c a b c a b c a b c a b c a b c a b c a b c a b c a b c a b c a b c', 'a...b...c', occurrence=16, tag='<b>', ignore_small_words=False)
        expected_text = 'a b c a b c a b c a b c a b c a b c a b c a b c a b c a b c a b c a b c a b c a b c a b c <b>a</b> <b>b</b> <b>c</b>'
        self.assertEqual(expected_text, marked_text)
        ruth_1_22 = 'So Naomi, the woman who returned from the fields of Moab, came back; and Ruth, the Moabite woman, her daughter-in-law, was with her. And they came to Bethlehem at the beginning of the harvest of barley.'
        marked_text = mark_phrases_in_html(ruth_1_22, 'the woman ... Moabite', occurrence=1, tag='<b>')
        expected_text = 'So Naomi, <b>the woman</b> who returned from the fields of Moab, came back; and Ruth, the <b>Moabite</b> woman, her daughter-in-law, was with her. And they came to Bethlehem at the beginning of the harvest of barley.'
        self.assertEqual(expected_text, marked_text)
        marked_text = mark_phrases_in_html(marked_text, 'woman', occurrence=2, tag='<b>')
        expected_text = 'So Naomi, <b>the woman</b> who returned from the fields of Moab, came back; and Ruth, the <b>Moabite</b> <b>woman</b>, her daughter-in-law, was with her. And they came to Bethlehem at the beginning of the harvest of barley.'
        self.assertEqual(expected_text, marked_text)
        marked_text = mark_phrases_in_html(marked_text, 'woman', occurrence=1, tag='<b>')
        expected_text = 'So Naomi, <b>the <b>woman</b></b> who returned from the fields of Moab, came back; and Ruth, the <b>Moabite</b> <b>woman</b>, her daughter-in-law, was with her. And they came to Bethlehem at the beginning of the harvest of barley.'
        self.assertEqual(expected_text, marked_text)

    def test_tw_and_tn_mark_phrase_in_html(self):
        html = '<div class="verse"><span class="v-num">2</span> But I went up because of a revelation and set before them the gospel that I proclaim among the Gentiles. I spoke privately to those who seemed to be important, in order to make sure that I was not running—or had not run—in vain.</div>'
        tw_phrases = {'revelation': 1, 'gospel': 1, 'proclaim': 1, 'Gentiles': 1, 'I was ... running': 1, 'had not run': 1, 'I': 1}
        tn_phrases = {'those who seemed to be important': 1, 'I was not running—or had not run—in vain': 1, 'in vain': 1}
        for phrase in tw_phrases:
            html = mark_phrases_in_html(html, phrase, tw_phrases[phrase], tag='<a class="tw-phrase" href="#test">')
        for phrase in tn_phrases:
            html = mark_phrases_in_html(html, phrase, tn_phrases[phrase], ignore_small_words=False)
        expected_html = '<div class="verse"><span class="v-num">2</span> But <a class="tw-phrase" href="#test">I</a> went up because of a <a class="tw-phrase" href="#test">revelation</a> and set before them the <a class="tw-phrase" href="#test">gospel</a> that I <a class="tw-phrase" href="#test">proclaim</a> among the <a class="tw-phrase" href="#test">Gentiles</a>. I spoke privately to <span class="highlight">those who seemed to be important</span>, in order to make sure that <a class="tw-phrase" href="#test"><span class="highlight">I was</span></a><span class="highlight"> not </span><a class="tw-phrase" href="#test"><span class="highlight">running</span></a><span class="highlight">—or </span><a class="tw-phrase" href="#test"><span class="highlight">had not run</span></a><span class="highlight">—<span class="highlight">in vain</span></span>.</div>'
        self.assertEqual(expected_html, html)

    def test_unnest_a_links(self):
        html = 'If you <a href="outer"> have <a href="inner"> two links</a>, only one </a> will be shown'
        expected = 'If you  <span class="nested-link nested-link-outer"><a href="outer">have</a>  <span class="nested-link nested-link-inner"><a href="inner">two links</a></span><a href="outer">, only one</a></span>  will be shown'
        unnested_html = unnest_a_links(html)
        self.assertEqual(expected, unnested_html)
        html = '<a href="outer-outer">' + html + '</a>'
        expected = '<span class="nested-link nested-link-outer"><a href="outer-outer">If you  <span class="nested-link nested-link-outer"></a><span class="nested-link nested-link-inner"><a href="outer">have</a>  <span class="nested-link nested-link-inner"><a href="inner">two links</a></span><a href="outer">, only one</a></span><a href="outer-outer"></span>  will be shown</a></span>'
        unnested_html = unnest_a_links(html)
        self.assertEqual(expected, unnested_html)

    def test_mark_phrase_in_html_with_punctuation_in_quote(self):
        html = '<div class="verse"><span class="v-num" id="en-ugnt-bible-tit-01-008"><sup><b>8</b></sup></span> ἀλλὰ φιλόξενον, φιλάγαθον, σώφρονα, δίκαιον, ὅσιον, ἐγκρατῆ;</div>'
        phrases = [[{'word': 'δίκαιον', 'occurrence': 1}, {'word': ',', 'occurrence': 4}, {'word': 'ὅσιον', 'occurrence': 1}]]
        phrases_string = 'δίκαιον, ὅσιον'
        highlighted_html = mark_phrases_in_html(html, phrases, phrases_string)
        expected = '<div class="verse"><span class="v-num" id="en-ugnt-bible-tit-01-008"><sup><b>8</b></sup></span> ἀλλὰ φιλόξενον, φιλάγαθον, σώφρονα, <span class="highlight">δίκαιον, ὅσιον</span>, ἐγκρατῆ;</div>'
        self.assertEqual(expected, highlighted_html)

        html = '<div class="verse"><span class="v-num" id="en-ugnt-bible-tit-01-004"><sup><b>4</b></sup></span> Τίτῳ, γνησίῳ τέκνῳ, κατὰ κοινὴν πίστιν: χάρις καὶ εἰρήνη ἀπὸ Θεοῦ Πατρὸς  καὶ Χριστοῦ Ἰησοῦ  τοῦ Σωτῆρος ἡμῶν.</div>'
        phrases = [[{'word': 'χάρις', 'occurrence': 1}, {'word': 'καὶ', 'occurrence': 1}, {'word': 'εἰρήνη', 'occurrence': 1}]]
        phrases_string = 'χάρις καὶ εἰρήνη'
        highlighted_html = mark_phrases_in_html(html, phrases, phrases_string)
        expected = '<div class="verse"><span class="v-num" id="en-ugnt-bible-tit-01-004"><sup><b>4</b></sup></span> Τίτῳ, γνησίῳ τέκνῳ, κατὰ κοινὴν πίστιν: <span class="highlight">χάρις καὶ εἰρήνη</span> ἀπὸ Θεοῦ Πατρὸς  καὶ Χριστοῦ Ἰησοῦ  τοῦ Σωτῆρος ἡμῶν.</div>'
        self.assertEqual(expected, highlighted_html)
