import os
import re
from steve_site.blog import markdown_converter


def get_release_note_html(limit=None):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, 'static', 'Release Notes.md')

    if not os.path.exists(file_path):
        return "<p>暂无更新日志</p>"

    with open(file_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    sections = re.split(r'(?=^##\s)', md_content, flags=re.M)
    h2_blocks = [sec for sec in sections if sec.startswith('## ')]
    if limit:
        top_h2_md = h2_blocks[:limit]
    else:
        top_h2_md = h2_blocks

    top_h2_html = [markdown_converter(_) for _ in top_h2_md]
    top_h2_html = [f'<div class="release-note-timeline-item">{_}</div>' for _ in top_h2_html]

    return ''.join(top_h2_html)
