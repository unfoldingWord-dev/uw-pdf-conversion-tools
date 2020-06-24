import os
import markdown2
from bs4 import BeautifulSoup


def get_obs_chapter_data(obs_dir, chapter_num):
    obs_chapter_data = {
        'title': None,
        'frames': [],
        'images': [],
        'bible_reference': None
    }
    obs_chapter_file = os.path.join(obs_dir, 'content', f'{chapter_num}.md')
    if os.path.isfile(obs_chapter_file):
        soup = BeautifulSoup(markdown2.markdown_path(os.path.join(obs_dir, 'content', f'{chapter_num}.md')),
                             'html.parser')
        obs_chapter_data['title'] = soup.h1.text
        paragraphs = soup.find_all('p')
        current_frame_text = '' 
        last_was_image = False
        for idx, p in enumerate(paragraphs):
            if p.img:            
                src = p.img['src'].split('?')[0]
                obs_chapter_data['images'].append(src)
                if current_frame_text:
                   obs_chapter_data['frames'].append(current_frame_text)
                   current_frame_text = ''
                last_was_image = True
            elif idx == len(paragraphs) - 1 and not last_was_image:
                obs_chapter_data['bible_reference'] = p.text
                last_was_image = False
            else:
                if current_frame_text:
                    current_frame_text += "<br/>\n<br/>\n"
                current_frame_text += p.text
                last_was_image = False
        if current_frame_text:
            obs_chapter_data['frames'].append(current_frame_text)
    return obs_chapter_data
