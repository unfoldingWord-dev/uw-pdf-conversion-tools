from unittest import TestCase
from .html_tools import mark_phrase_in_text


class Test(TestCase):
    def test_mark_phrase_in_text(self):
        marked_text = mark_phrase_in_text('here I am', 'I')
        self.assertEqual(marked_text, 'here <span class="highlight">I</span> am')
        marked_text = mark_phrase_in_text('here I now am', 'I...am')
        self.assertEqual(marked_text, 'here I now <span class="highlight">am</span>')
        marked_text = mark_phrase_in_text('here I now am', 'I...am', ignore_small_words=False)
        self.assertEqual(marked_text, 'here <span class="highlight">I</span> now <span class="highlight">am</span>')
        marked_text = mark_phrase_in_text('to be or not to be that is the question', 'to be', occurrence=2)
        self.assertEqual(marked_text, 'to be or not <span class="highlight">to be</span> that is the question')
        marked_text = mark_phrase_in_text('a b c a b c a b c a b c a b c a b c a b c a b c a b c a b c a b c a b c a b c a b c a b c a b c', 'a...b...c', occurrence=16, tag='<b>', ignore_small_words=False)
        self.assertEqual(marked_text, 'a b c a b c a b c a b c a b c a b c a b c a b c a b c a b c a b c a b c a b c a b c a b c <b>a</b> <b>b</b> <b>c</b>')
        ruth_1_22 = 'So Naomi, the woman who returned from the fields of Moab, came back; and Ruth, the Moabite woman, her daughter-in-law, was with her. And they came to Bethlehem at the beginning of the harvest of barley.'
        marked_text = mark_phrase_in_text(ruth_1_22, 'the woman ... Moabite', occurrence=1, tag='<b>')
        self.assertEqual(marked_text, 'So Naomi, <b>the woman</b> who returned from the fields of Moab, came back; and Ruth, the <b>Moabite</b> woman, her daughter-in-law, was with her. And they came to Bethlehem at the beginning of the harvest of barley.')
        marked_text = mark_phrase_in_text(marked_text, 'woman', occurrence=2, tag='<b>')
        self.assertEqual(marked_text, 'So Naomi, <b>the woman</b> who returned from the fields of Moab, came back; and Ruth, the <b>Moabite</b> <b>woman</b>, her daughter-in-law, was with her. And they came to Bethlehem at the beginning of the harvest of barley.')
        marked_text = mark_phrase_in_text(marked_text, 'woman', occurrence=1, tag='<b>')
        self.assertEqual(marked_text, 'So Naomi, <b>the <b>woman</b></b> who returned from the fields of Moab, came back; and Ruth, the <b>Moabite</b> <b>woman</b>, her daughter-in-law, was with her. And they came to Bethlehem at the beginning of the harvest of barley.')
