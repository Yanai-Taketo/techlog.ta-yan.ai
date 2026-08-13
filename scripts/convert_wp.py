#!/usr/bin/env python3
"""WordPress (SANGO theme) -> Markdown converter for techlog.ta-yan.ai migration.

Reads the WordPress DB (imported into local MariaDB) and emits:
  - content/blog/<YYYYMMDD><ID>.md   (Japanese posts, publish only)
  - content/pages/<slug>.md          (fixed pages)
  - referenced_uploads.txt           (image files to extract from backup zip)
  - redirects_en.txt                 (old English URL -> Japanese URL)
  - report.txt                       (conversion audit)
"""
import pymysql, re, os, sys, json, html
from collections import Counter
from bs4 import BeautifulSoup, NavigableString, Comment, Tag

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'converted')
BLOG_DIR = os.path.join(OUT, 'blog')
PAGES_DIR = os.path.join(OUT, 'pages')
os.makedirs(BLOG_DIR, exist_ok=True)
os.makedirs(PAGES_DIR, exist_ok=True)

SITE = 'https://techlog.ta-yan.ai'
report = []
referenced_uploads = set()

conn = pymysql.connect(host='localhost', user='root', db='techlog', charset='utf8mb4',
                       unix_socket='/var/run/mysqld/mysqld.sock')
cur = conn.cursor()

# ---- zip file listing (originals available) --------------------------------
import subprocess
zip_list = subprocess.run(['unzip', '-Z1', 'box_2404953771744.bin'],
                          capture_output=True, text=True,
                          cwd=os.path.dirname(os.path.abspath(__file__))).stdout.splitlines()
zip_files = set(z[len('techlog/'):] for z in zip_list if z.startswith('techlog/'))

def uploads_exists(relpath):
    return relpath.lstrip('/') in zip_files

# ---- helpers ----------------------------------------------------------------

def get_meta(post_id, key):
    cur.execute("SELECT meta_value FROM wp_postmeta WHERE post_id=%s AND meta_key=%s LIMIT 1", (post_id, key))
    r = cur.fetchone()
    return r[0] if r else None

def get_categories(post_id):
    cur.execute("""
        SELECT t.name FROM wp_term_relationships tr
        JOIN wp_term_taxonomy tt ON tt.term_taxonomy_id = tr.term_taxonomy_id AND tt.taxonomy='category'
        JOIN wp_terms t ON t.term_id = tt.term_id
        WHERE tr.object_id=%s ORDER BY t.term_id""", (post_id,))
    return [r[0] for r in cur.fetchall() if r[0] != '未分類']

def featured_image(post_id):
    tid = get_meta(post_id, '_thumbnail_id')
    if not tid:
        return None
    f = get_meta(int(tid), '_wp_attached_file')
    if not f:
        return None
    rel = f'wp-content/uploads/{f}'
    if uploads_exists(rel):
        referenced_uploads.add(rel)
        return '/' + rel
    return None

SIZE_SUFFIX = re.compile(r'-\d+x\d+(?=\.(?:jpe?g|png|gif|webp)$)', re.I)

def normalize_upload(src):
    """Make techlog upload URLs root-relative; prefer original over -WxH thumbnail."""
    src = src.split('?')[0]
    if src.startswith(SITE):
        src = src[len(SITE):]
    if not src.startswith('/wp-content/uploads/'):
        return src  # external
    rel = src.lstrip('/')
    orig = SIZE_SUFFIX.sub('', rel)
    if orig != rel and uploads_exists(orig):
        referenced_uploads.add(orig)
        return '/' + orig
    if uploads_exists(rel):
        referenced_uploads.add(rel)
        return '/' + rel
    # repair truncated extension (e.g. ".../abc." -> ".../abc.png")
    for ext in ('png', 'jpg', 'jpeg', 'webp', 'gif'):
        cand = rel.rstrip('.') + '.' + ext
        if uploads_exists(cand):
            referenced_uploads.add(cand)
            return '/' + cand
    report.append(f'MISSING UPLOAD: {rel}')
    return '/' + rel

def rel_link(href):
    if href and href.startswith(SITE):
        rest = href[len(SITE):]
        return rest if rest else '/'
    return href

def esc_text(s):
    """Escape markdown/HTML-sensitive chars in prose text."""
    s = s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return s

def esc_attr(s):
    return (s or '').replace('"', "'").strip()

def dir_label(s):
    return (s or '').replace('[', '(').replace(']', ')').strip()


def wrap_directive(kind, attr, inner):
    fence = ':::'
    while re.search(r'^' + re.escape(fence), inner, re.M):
        fence += ':'
    return f'{fence}{kind}{attr}\n{inner}\n{fence}'

# ---- inline conversion ------------------------------------------------------

def inline(node):
    """Convert an element's children to markdown inline text."""
    parts = []
    for c in node.children:
        if isinstance(c, Comment):
            continue
        if isinstance(c, NavigableString):
            parts.append(esc_text(str(c)))
            continue
        name = c.name
        if name in ('strong', 'b'):
            t = inline(c).strip()
            parts.append(f'**{t}**' if t else '')
        elif name in ('em', 'i'):
            if 'fa' in (c.get('class') or []) or (c.get('class') and any(k.startswith('fa') for k in c.get('class'))):
                continue  # font-awesome icon
            t = inline(c).strip()
            parts.append(f'*{t}*' if t else '')
        elif name == 'code':
            t = c.get_text()
            fence = '``' if '`' in t else '`'
            parts.append(f'{fence}{t}{fence}')
        elif name == 'a':
            href = rel_link(c.get('href', ''))
            t = inline(c).strip() or href
            parts.append(f'[{t}]({href})')
        elif name == 'br':
            parts.append('<br>')
        elif name == 'img':
            src = normalize_upload(c.get('src', ''))
            alt = esc_attr(c.get('alt', ''))
            parts.append(f'![{alt}]({src})')
        elif name in ('del', 's', 'strike'):
            parts.append(f'~~{inline(c).strip()}~~')
        elif name in ('span', 'u', 'small', 'mark', 'sub', 'sup', 'font', 'center'):
            parts.append(inline(c))
        else:
            parts.append(inline(c))
    return ''.join(parts)

# ---- block conversion -------------------------------------------------------

def convert_list(el, indent=0):
    lines = []
    ordered = el.name == 'ol'
    n = 0
    for li in el.find_all('li', recursive=False):
        n += 1
        marker = f'{n}.' if ordered else '-'
        sublists = li.find_all(['ul', 'ol'], recursive=False)
        for s in sublists:
            s.extract()
        text = inline(li).strip().replace('\n', ' ')
        lines.append('  ' * indent + f'{marker} {text}')
        for s in sublists:
            lines.extend(convert_list(s, indent + 1))
    return lines

def convert_table(el):
    table = el if el.name == 'table' else el.find('table')
    if table is None:
        return ''
    # bail to raw HTML if complex
    if table.find(attrs={'colspan': True}) or table.find(attrs={'rowspan': True}):
        for t in table.find_all(True):
            for a in list(t.attrs):
                if a not in ('href', 'src', 'colspan', 'rowspan'):
                    del t.attrs[a]
        report.append('RAW TABLE kept (colspan/rowspan)')
        return str(table)
    rows = table.find_all('tr')
    if not rows:
        return ''
    md = []
    header_cells = rows[0].find_all(['th', 'td'])
    ncol = len(header_cells)
    is_header = rows[0].find('th') is not None
    def cells(tr):
        return [inline(td).strip().replace('\n', ' ').replace('|', '\\|') for td in tr.find_all(['th', 'td'])]
    if is_header:
        md.append('| ' + ' | '.join(cells(rows[0])) + ' |')
        body = rows[1:]
    else:
        md.append('| ' + ' | '.join([''] * ncol) + ' |')
        body = rows
    md.append('|' + '---|' * ncol)
    for tr in body:
        md.append('| ' + ' | '.join(cells(tr)) + ' |')
    return '\n'.join(md)

LANG_MAP = {
    'powershell': 'powershell', 'power shell': 'powershell', 'ps': 'powershell',
    'cmd': 'bat', 'bat': 'bat', 'batch': 'bat', 'コマンド': 'bat', 'コマンドプロンプト': 'bat',
    'vb.net': 'vb', 'vb': 'vb', 'vbnet': 'vb', 'vba': 'vb',
    'python': 'python', 'py': 'python',
    'bash': 'bash', 'shell': 'bash', 'sh': 'bash', 'terminal': 'bash', 'ターミナル': 'bash',
    'html': 'html', 'css': 'css', 'javascript': 'js', 'js': 'js', 'json': 'json',
    'sql': 'sql', 'yaml': 'yaml', 'xml': 'xml', 'ini': 'ini', 'conf': 'ini', 'config': 'ini',
    'text': 'text',
}

def codebox_lang(title):
    t = (title or '').strip().lower()
    return LANG_MAP.get(t, '')

def convert_codebox(el):
    title = ''
    span = el.find('span', recursive=False)
    if span:
        title = span.get_text().strip()
    code_el = el.find('code') or el.find('pre')
    code = code_el.get_text() if code_el else ''
    code = code.rstrip('\n')
    lang = codebox_lang(title) or 'text'
    out = []
    if title:
        out.append(f'<div class="code-label">{esc_text(title)}</div>')
        out.append('')
    fence = '````' if '```' in code else '```'
    out.append(f'{fence}{lang}')
    out.append(code)
    out.append(fence)
    return '\n'.join(out)

def heading_from_sgb(el, default_level):
    txt_el = el.find(class_='sgb-heading__text')
    text = (txt_el.get_text() if txt_el else el.get_text()).strip()
    if el.name in ('h2', 'h3', 'h4'):
        level = int(el.name[1])
    else:
        level = default_level
    return '#' * level + ' ' + esc_text(text)

def convert_image_figure(el):
    img = el.find('img')
    if img is None:
        return ''
    src = normalize_upload(img.get('src', ''))
    alt = esc_attr(img.get('alt', ''))
    cap_el = el.find('figcaption')
    if cap_el:
        cap = inline(cap_el).strip()
        return f'<figure>\n\n![{alt}]({src})\n\n<figcaption>{cap}</figcaption>\n</figure>'
    return f'![{alt}]({src})'

def convert_block(el, ctx):
    """Convert a block-level element to markdown. Returns str or None."""
    if isinstance(el, Comment):
        return None
    if isinstance(el, NavigableString):
        t = str(el).strip()
        return esc_text(t) if t else None
    cls = el.get('class') or []
    name = el.name

    if 'wp-block-sgb-headings' in cls or 'sgb-heading' in cls:
        return heading_from_sgb(el, ctx['p_heading_level'])
    if 'wp-block-sgb-codebox' in cls:
        return convert_codebox(el)
    if 'wp-block-code' in cls:
        code = (el.find('code') or el).get_text().rstrip('\n')
        fence = '````' if '```' in code else '```'
        return f'{fence}text\n{code}\n{fence}'
    if 'wp-block-sgb-block-simple' in cls:
        title_el = el.find(class_='sgb-box-simple__title')
        body = el.find(class_='sgb-box-simple__body') or el
        title = title_el.get_text().strip() if title_el else ''
        inner = convert_children(body, ctx)
        attr = f'{{title="{esc_attr(title)}"}}' if title else ''
        return wrap_directive('box', attr, inner)
    if 'wp-block-sgb-message' in cls:
        title_el = el.find(class_='sng-box-msg__title')
        icon = el.find('i')
        icon_cls = ' '.join(icon.get('class') or []) if icon else ''
        kind = 'alert' if ('exclamation' in icon_cls or 'warning' in icon_cls or 'times' in icon_cls) else 'memo'
        body = el.find(class_='sng-box-msg__contents') or el
        title = title_el.get_text().strip() if title_el else ''
        inner = convert_children(body, ctx)
        attr = f'{{title="{esc_attr(title)}"}}' if title else ''
        return wrap_directive(kind, attr, inner)
    if 'wp-block-sgb-box' in cls or 'sng-box' in cls:
        inner = convert_children(el, ctx)
        return wrap_directive('box', '', inner)
    if 'wp-block-sgb-sanko' in cls:
        return None  # handled from block comment attrs (pre-extracted); fallback below
    if 'wp-block-sgb-list' in cls:
        lst = el.find(['ul', 'ol'])
        return '\n'.join(convert_list(lst)) if lst else None
    if name == 'hr' or 'wp-block-sgb-sen' in cls or 'wp-block-separator' in cls:
        return '---'
    if 'wp-block-image' in cls or (name == 'figure' and el.find('img')):
        return convert_image_figure(el)
    if 'wp-block-gallery' in cls:
        out = []
        for fig in el.find_all('figure'):
            out.append(convert_image_figure(fig))
        return '\n\n'.join(out)
    if name == 'figure' and (el.find('table') is not None):
        return convert_table(el)
    if name == 'table':
        return convert_table(el)
    if name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
        return '#' * int(name[1]) + ' ' + inline(el).strip()
    if name in ('ul', 'ol'):
        return '\n'.join(convert_list(el))
    if name == 'blockquote':
        inner = convert_children(el, ctx)
        cite = el.get('cite', '')
        q = '\n'.join('> ' + l for l in inner.split('\n'))
        if cite:
            q += f'\n>\n> — <{cite}>'
        return q
    if name == 'pre':
        code = el.get_text().rstrip('\n')
        fence = '````' if '```' in code else '```'
        return f'{fence}text\n{code}\n{fence}'
    if name == 'p':
        t = inline(el).strip()
        return t if t else None
    if name in ('div', 'center', 'section', 'article', 'aside', 'main'):
        return convert_children(el, ctx)
    if name in ('iframe', 'script', 'video', 'audio', 'embed', 'object'):
        report.append(f'RAW ELEMENT kept: <{name}> {str(el)[:100]}')
        return str(el)
    # unknown
    report.append(f'UNKNOWN ELEMENT <{name}> class={cls} -> inline conversion')
    t = inline(el).strip()
    return t if t else None

def convert_children(parent, ctx):
    out = []
    for c in parent.children:
        r = convert_block(c, ctx)
        if r:
            out.append(r)
    return '\n\n'.join(out)

# ---- sanko (link card) pre-extraction --------------------------------------
SANKO_RE = re.compile(r'<!-- wp:sgb/sanko (\{.*?\}) -->(.*?)<!-- /wp:sgb/sanko -->', re.S)
CF7_RE = re.compile(r'<!-- wp:contact-form-7/contact-form-selector.*?<!-- /wp:contact-form-7/contact-form-selector -->', re.S)
TOC_RE = re.compile(r'<!-- wp:sgb/toc-inserter -->.*?<!-- /wp:sgb/toc-inserter -->', re.S)

sanko_tokens = {}

def sanko_replace(m):
    try:
        attrs = json.loads(m.group(1))
    except Exception:
        report.append('SANKO json parse failed')
        return ''
    url = attrs.get('url', '')
    title = dir_label(attrs.get('title', '') or url)
    site = esc_attr(attrs.get('siteName', ''))
    img = attrs.get('imageUrl', '') or ''
    img_attr = ''
    if img.startswith(SITE) or img.startswith('/wp-content/'):
        norm = normalize_upload(img)
        if not norm.startswith('http'):
            img_attr = f' image="{norm}"'
    site_attr = f' site="{site}"' if site else ''
    directive = f'::linkcard[{title}]{{url="{url}"{site_attr}{img_attr}}}'
    token = f'SANKOTOKEN{len(sanko_tokens)}X'
    sanko_tokens[token] = directive
    return f'\n<p></p>\n<p>{token}</p>\n<p></p>\n'

def preprocess(content):
    content = content.replace('\\n', '\n') if '\\n' in content and '<' not in content.split('\\n')[0] else content
    content = CF7_RE.sub('', content)
    content = TOC_RE.sub('', content)
    content = SANKO_RE.sub(sanko_replace, content)
    return content

# ---- shortcode handling on markdown ----------------------------------------
def shortcodes(md):
    md = re.sub(r'\[sng_toc_insert\]', '', md)
    md = re.sub(r'\[contact-form-7[^\]]*\]', '', md)
    def memo_rep(m):
        title = m.group(1) or 'MEMO'
        body = m.group(2).strip()
        return wrap_directive('memo', f'{{title="{esc_attr(title)}"}}', body)
    md = re.sub(r'\[memo(?:\s+title="([^"]*)")?\](.*?)\[/memo\]', memo_rep, md, flags=re.S)
    def box_rep(m):
        title = m.group(1)
        body = m.group(2).strip()
        attr = f'{{title="{esc_attr(title)}"}}' if title else ''
        return wrap_directive('box', attr, body)
    md = re.sub(r'\[box[^\]]*?(?:title="([^"]*)")?[^\]]*\](.*?)\[/box\]', box_rep, md, flags=re.S)
    return md

def tidy(md):
    md = re.sub(r'\n{3,}', '\n\n', md)
    md = re.sub(r'<p></p>\n?', '', md)
    md = re.sub(r'\n{3,}', '\n\n', md)
    return md.strip() + '\n'

def convert_content(content):
    sanko_tokens.clear()
    content = preprocess(content)
    # heading level rule: if the post uses h2-rendered sgb headings or core h2, p-rendered ones become h3
    has_h2 = bool(re.search(r'<h2[ >]', content))
    ctx = {'p_heading_level': 3 if has_h2 else 2}
    soup = BeautifulSoup(content, 'html.parser')
    for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    md = convert_children(soup, ctx)
    md = shortcodes(md)
    for token, directive in sanko_tokens.items():
        md = md.replace(token, directive)
    return tidy(md)

def first_paragraph_text(md, limit=120):
    for line in md.split('\n'):
        l = line.strip()
        if not l or l.startswith(('#', ':::', '::', '!', '```', '|', '---', '>', '<')):
            continue
        t = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', l)
        t = re.sub(r'[*_`]', '', t)
        t = html.unescape(t)
        t = re.sub(r'<[^>]+>', '', t)
        if len(t) > limit:
            t = t[:limit].rstrip() + '…'
        return t
    return ''

def yaml_str(s):
    return json.dumps(s, ensure_ascii=False)

# ---- posts ------------------------------------------------------------------
cur.execute("""
    SELECT p.ID, p.post_title, p.post_content, p.post_date, p.post_modified, p.post_excerpt
    FROM wp_posts p
    WHERE p.post_type='post' AND p.post_status='publish'
    ORDER BY p.post_date""")
posts = cur.fetchall()

ja_posts = []
en_posts = []
for pid, title, content, pdate, pmod, excerpt in posts:
    locale = get_meta(pid, '_locale')
    if locale == 'en_US':
        en_posts.append((pid, title, pdate))
    else:
        ja_posts.append((pid, title, content, pdate, pmod, excerpt))

print(f'JA posts: {len(ja_posts)}, EN posts: {len(en_posts)}')

path_by_id = {}
for pid, title, content, pdate, pmod, excerpt in ja_posts:
    code = pdate.strftime('%Y%m%d') + str(pid)
    path_by_id[pid] = f'/{code}/'

for pid, title, content, pdate, pmod, excerpt in ja_posts:
    code = pdate.strftime('%Y%m%d') + str(pid)
    md = convert_content(content)
    cats = get_categories(pid)
    img = featured_image(pid)
    desc = get_meta(pid, 'sng_meta_description') or (excerpt or '').strip() or first_paragraph_text(md)
    fm = ['---']
    fm.append(f'title: {yaml_str(title)}')
    fm.append(f'description: {yaml_str(desc)}')
    fm.append(f'pubDate: {pdate.strftime("%Y-%m-%dT%H:%M:%S+09:00")}')
    if pmod and pmod > pdate:
        fm.append(f'updatedDate: {pmod.strftime("%Y-%m-%dT%H:%M:%S+09:00")}')
    fm.append('categories: [' + ', '.join(yaml_str(c) for c in cats) + ']')
    if img:
        fm.append(f'image: {yaml_str(img)}')
    fm.append(f'wpId: {pid}')
    fm.append('---')
    with open(os.path.join(BLOG_DIR, f'{code}.md'), 'w') as f:
        f.write('\n'.join(fm) + '\n\n' + md)

# ---- pages ------------------------------------------------------------------
for pid, slug in ((114, 'info'), (373, 'logo-guidelines')):
    cur.execute("SELECT post_title, post_content, post_date, post_modified FROM wp_posts WHERE ID=%s", (pid,))
    title, content, pdate, pmod = cur.fetchone()
    md = convert_content(content)
    fm = ['---', f'title: {yaml_str(title)}',
          f'description: {yaml_str(first_paragraph_text(md))}',
          f'pubDate: {pdate.strftime("%Y-%m-%dT%H:%M:%S+09:00")}', '---']
    with open(os.path.join(PAGES_DIR, f'{slug}.md'), 'w') as f:
        f.write('\n'.join(fm) + '\n\n' + md)

# ---- EN -> JA redirect map --------------------------------------------------
redirects = []
for pid, title, pdate in en_posts:
    code = pdate.strftime('%Y%m%d') + str(pid)
    orig = get_meta(pid, '_original_post') or ''
    m = re.search(r'[?&]p=(\d+)', orig)
    target = '/'
    if m and int(m.group(1)) in path_by_id:
        target = path_by_id[int(m.group(1))]
    redirects.append(f'/en/{code}/ {target} 301')
    redirects.append(f'/{code}/ {target} 301')  # in case EN was served without prefix
with open(os.path.join(OUT, 'redirects_en.txt'), 'w') as f:
    f.write('\n'.join(redirects) + '\n')

with open(os.path.join(OUT, 'referenced_uploads.txt'), 'w') as f:
    f.write('\n'.join(sorted(referenced_uploads)) + '\n')

with open(os.path.join(OUT, 'report.txt'), 'w') as f:
    f.write('\n'.join(report) + '\n')

print(f'uploads referenced: {len(referenced_uploads)}')
print(f'report lines: {len(report)}')
for line in report[:30]:
    print(' !', line)
