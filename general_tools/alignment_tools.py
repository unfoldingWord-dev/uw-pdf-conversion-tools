#!/usr/bin/env python3
#
#  Copyright (c) 2020 unfoldingWord
#  http://creativecommons.org/licenses/MIT/
#  See LICENSE file for details.
#
#  Contributors:
#  Richard Mahn <rich.mahn@unfoldingword.org>

import re
from general_tools.file_utils import load_json_object


def get_quote_combinations(quote):
    quote_combinations = []
    for i in range(0, len(quote)):
        indexes = [i]
        text = [quote[i]['word']]
        quote_combinations.append({
            'text': text[:],
            'occurrence': quote[i]['occurrence'],
            'indexes': indexes[:],
            'found': False
        })
        for j in range(i + 1, len(quote)):
            indexes.append(j)
            text.append(quote[j]["word"])
            quote_combinations.append({
                'text': text[:],
                'occurrence': 1,
                'indexes': indexes[:],
                'found': False
            })
    return quote_combinations


def split_string_into_quote(string, occurrence=1):
    quote = []
    parts = re.split(r'\s*…\s*|\s*\.\.\.\s*|\s+', string)
    for part in parts:
        quote.append({
            'word': part,
            'occurrence': occurrence
        })
    return quote


def get_alignment(verse_objects, quote, occurrence=1):
    orig_quote = quote
    if isinstance(quote, str):
        quote = split_string_into_quote(quote, occurrence)
    else:
        quote = []
        for word in orig_quote:
            if 'word' in word and word['word'] != '…' and 'occurrence' in word:
                quote.append({
                    'word': word['word'],
                    'occurrence': word['occurrence']
                })
    quote_combinations = get_quote_combinations(quote)
    alignment = get_alignment_by_combinations(verse_objects, quote, quote_combinations)
    for word in quote:
        if 'found' not in word:
            return None
    return alignment


def get_alignment_by_combinations(verse_objects, quote, quote_combinations, found=False):
    alignments = []
    in_between_alignments = []
    last_found = False
    for verse_object in verse_objects:
        my_found = found
        if 'type' in verse_object and verse_object['type'] == 'milestone':
            if 'content' in verse_object:
                for combo in quote_combinations:
                    joined_with_spaces = ' '.join(combo['text'])
                    joined_with_joiner = '\u2060'.join(combo['text'])
                    if not combo['found'] and \
                        combo['occurrence'] == verse_object['occurrence'] and \
                            (joined_with_spaces == verse_object['content'] or
                             joined_with_joiner == verse_object['content']):
                        all_done = True
                        for index in combo['indexes']:
                            if 'found' in quote[index] and quote[index]['found']:
                                all_done = False
                        if all_done:
                            my_found = True
                            combo['found'] = True
                            for index in combo['indexes']:
                                quote[index]['found'] = True
                            break
                if not my_found:
                    last_found = False
                    in_between_alignments = []
            if 'children' in verse_object:
                my_alignments = get_alignment_by_combinations(verse_object['children'], quote, quote_combinations,
                                                              my_found)
                if not found and my_found:
                    if last_found:
                        alignments[-1] += in_between_alignments + my_alignments
                        in_between_alignments = []
                    else:
                        alignments.append(my_alignments)
                        last_found = True
                else:
                    alignments += my_alignments
        elif 'text' in verse_object and (found or last_found):
            alignment = {
                'text': verse_object['text'],
                'occurrence': verse_object['occurrence'] if 'occurrence' in verse_object else 0
            }
            if found:
                alignments.append(alignment)
            elif last_found:
                in_between_alignments.append(alignment)
    return alignments


def flatten_quote(quote):
    if not quote:
        return quote
    if isinstance(quote, str):
        return quote
    words = []
    for word in quote:
        words.append(word['word'])
    return '…'.join(words)


def flatten_alignment(alignment):
    if not alignment:
        return alignment
    if isinstance(alignment, str):
        return alignment
    part_strs = []
    for part in alignment:
        words = ''
        for word in part:
            words += word['text']
        part_strs.append(words)
    return ' … '.join(part_strs)


def tests():
    # TIT	1	2	r2gj		πρὸ χρόνων αἰωνίων	1	before all the ages of time
    chapter_verse_objects = load_json_object('/Users/richmahn/working/resources/en/bibles/ult/v8/tit/1.json')
    quote = 'πρὸ χρόνων αἰωνίων'
    occurrence = 1
    verse_objects = chapter_verse_objects["2"]["verseObjects"]
    alignments = get_alignment(verse_objects, quote, occurrence)
    print(alignments)
    return

    string = 'בִּ⁠ימֵי֙ שְׁפֹ֣ט הַ⁠שֹּׁפְטִ֔ים'
    group_data = load_json_object(
        '/Users/richmahn/working/resources/en/translationHelps/translationNotes/v23/other/groups/rut/grammar-connect-time-simultaneous.json')
    chapter_verse_objects = load_json_object('/Users/richmahn/working/resources/en/bibles/ult/v8/rut/1.json')

    quote = group_data[0]["contextId"]["quote"]
    verse_objects = chapter_verse_objects["1"]["verseObjects"]
    alignments = get_alignment(verse_objects, quote)
    print(alignments)


    # RUT	4	22	abcd	figs-explicit	אֶת־דָּוִֽד	1	David
    group_data = load_json_object(
        '/Users/richmahn/working/resources/en/translationHelps/translationNotes/v23/culture/groups/rut/figs-explicit.json')
    chapter_verse_objects = load_json_object('/Users/richmahn/working/resources/en/bibles/ult/v8/rut/4.json')

    quote = group_data[12]["contextId"]["quote"]
    occurrence = group_data[12]["contextId"]["occurrence"]
    verse_objects = chapter_verse_objects["22"]["verseObjects"]
    alignments = get_alignment(verse_objects, quote, occurrence)
    print(alignments)

    # RUT	4	17	f9ha	figs-explicit	אֲבִ֥י דָוִֽד	1	the father of David
    quote = group_data[11]["contextId"]["quote"]
    occurrence = group_data[11]["contextId"]["occurrence"]
    verse_objects = chapter_verse_objects["17"]["verseObjects"]
    alignments = get_alignment(verse_objects, quote, occurrence)
    print(alignments)

    # RUT	4	19	rl3k	translate-names	וְ⁠חֶצְרוֹן֙…עַמִּֽינָדָֽב׃	1	Hezron…Amminadab
    group_data = load_json_object(
        '/Users/richmahn/working/resources/en/translationHelps/translationNotes/v23/culture/groups/rut/translate-names.json')
    quote = group_data[-1]["contextId"]["quote"]
    occurrence = group_data[-1]["contextId"]["occurrence"]
    verse_objects = chapter_verse_objects["17"]["verseObjects"]
    alignments = get_alignment(verse_objects, quote, occurrence)
    print(alignments)

    # RUT	1	4	aee6		שֵׁ֤ם הָֽ⁠אַחַת֙…וְ⁠שֵׁ֥ם הַ⁠שֵּׁנִ֖י	1	the name of the first woman was…and the name of the second woman was
    quote = 'שֵׁ֤ם הָֽ⁠אַחַת֙…וְ⁠שֵׁ֥ם הַ⁠שֵּׁנִ֖י'
    occurrence = 1
    chapter_verse_objects = load_json_object('/Users/richmahn/working/resources/en/bibles/ult/v8/rut/1.json')
    verse_objects = chapter_verse_objects["4"]["verseObjects"]
    alignments = get_alignment(verse_objects, quote, occurrence)
    print(alignments)
