# coding=utf-8

from __future__ import unicode_literals
import re


def usfm3_to_usfm2(usfm3):
    """
    Converts a USFM 3 string to a USFM 2 compatible string
    :param usfm3:
    :return: the USFM 2 version of the string
    """
    # Kind of usfm3 to usfm2
    usfm2 = re.sub(r'\\ts(-s)*\s*\\\*\s*', r'', usfm3, flags=re.UNICODE | re.MULTILINE)
    usfm2 = re.sub(r'\\zaln-s[^*]*\*', r'', usfm2, flags=re.UNICODE | re.MULTILINE)
    usfm2 = re.sub(r'\\zaln-e\\\*', r'', usfm2, flags=re.UNICODE | re.MULTILINE)
    usfm2 = re.sub(r'\\w ([^|]+)\|.*?\\w\*', r'\1', usfm2, flags=re.UNICODE | re.MULTILINE)
    usfm2 = re.sub(r'^\n', '', usfm2, flags=re.UNICODE | re.MULTILINE)
    usfm2 = re.sub(r'^([^\\].*)\n(?=[^\\])', r'\1 ', usfm2, flags=re.UNICODE | re.MULTILINE)
    usfm2 = re.sub(r'^\\(.*)\n(?=[^\\])', r'\\\1 ', usfm2, flags=re.UNICODE | re.MULTILINE)
    usfm2 = re.sub(r'  +', ' ', usfm2, flags=re.UNICODE | re.MULTILINE)

    # Clean up bad USFM data and fixing punctuation
    usfm2 = re.sub(r"\s*' s(?!\w)", "'s", usfm2, flags=re.UNICODE | re.MULTILINE)
    usfm2 = re.sub(r'\\s5', '', usfm2, flags=re.UNICODE | re.MULTILINE)
    usfm2 = re.sub(r'\\fqa([^*]+)\\fqa(?![*])', r'\\fqa\1\\fqa*', usfm2, flags=re.UNICODE | re.MULTILINE)
    
    # Pair up quotes by chapter
    chapters = re.compile(r'\\c').split(usfm2)
    usfm2 = chapters[0]
    for chapter in chapters[1:]:
        chapter = re.sub(r'\s*"\s*([^"]+)\s*"\s*', r' "\1" ', chapter, flags=re.UNICODE | re.MULTILINE | re.DOTALL)
        usfm2 += f'\\c{chapter}'
    usfm2 = re.sub(r'\\(\w+\**)([^\w* \n])', r'\\\1 \2', usfm2, flags=re.UNICODE | re.MULTILINE)  # \\q1" => \q1 "
    usfm2 = re.sub(r" ' ", r" '", usfm2, flags=re.UNICODE | re.MULTILINE)
    usfm2 = re.sub(r' +([:;.?,!\]})-])', r'\1', usfm2, flags=re.UNICODE | re.MULTILINE)
    usfm2 = re.sub(r'([{(\[-]) +', r'\1', usfm2, flags=re.UNICODE | re.MULTILINE)

    return usfm2.strip()
