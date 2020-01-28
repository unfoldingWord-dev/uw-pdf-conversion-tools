#!/usr/bin/env python3
# -*- coding: utf8 -*-

def html_update(input_html):
    from bs4 import BeautifulSoup
    import re

    soup = BeautifulSoup(input_html)

    replacement_list = [
        ('foo', '<span title="foo" class="customclass34 replace">', '</span>'),
        ('foo bar', '<span id="id21" class="customclass79 replace">', '</span>')
    ]
    # Go through list in order of decreasing length
    replacement_list = sorted(replacement_list, key=lambda k: -len(k[0]))

    for item in replacement_list:
        replace_regex = re.compile(item[0], re.IGNORECASE)
        target = soup.find_all(string=replace_regex)
        for v in target:
            # You can use other conditions here, like (v.parent.name == 'a')
            # to not wrap the tags around strings within links
            if v.parent.has_attr('class') and 'replace' in v.parent['class']:
                # The match must be part of a large string that was already replaced, so do nothing
                continue

            def replace(match):
                return '{0}{1}{2}'.format(item[1], match.group(0), item[2])

            new_v = replace_regex.sub(replace, v)
            v.replace_with(BeautifulSoup(new_v, 'html.parser'))
    return str(soup)

print(html_update('this is foo <span>bar</span>'))
