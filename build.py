#!/usr/bin/env python3
"""
将 .md 文件转换为 .html，不依赖 Jekyll。
处理尖括号链接语法 (<url>) 和中文路径。
"""
import os
import re
import glob
import shutil
import urllib.parse

ROOT = os.environ.get('ROOT', '/opt/buildhome/repo')
OUTPUT = os.environ.get('OUTPUT', '/opt/buildhome/repo/_site')

def encode_url(path):
    """URL 编码路径，但保留 / 和常见字符"""
    # 如果已经是 http 开头，不编码
    if path.startswith('http://') or path.startswith('https://'):
        return path
    # 分割路径，分别编码每一段
    parts = path.split('/')
    encoded_parts = []
    for part in parts:
        if part:
            encoded_parts.append(urllib.parse.quote(part, safe=''))
    return '/'.join(encoded_parts)

def parse_markdown_links(text):
    """
    解析 markdown 链接和图片，支持尖括号语法和嵌套方括号。
    返回替换后的 HTML。不编码 URL，留给后续处理。
    """
    result = []
    pos = 0

    # 匹配 ![alt](<url>) 或 [text](<url>)
    # 用 .+? 非贪婪匹配，支持文本中包含 ] 字符
    pattern = re.compile(
        r'(!?)\[(.+?)\]\((<[^>]+>|[^)]+)\)'
    )

    for match in pattern.finditer(text):
        # 添加匹配前的普通文本
        result.append(text[pos:match.start()])

        is_image = match.group(1) == '!'
        alt_or_text = match.group(2)
        raw_url = match.group(3)

        # 去掉尖括号
        if raw_url.startswith('<') and raw_url.endswith('>'):
            url = raw_url[1:-1]
        else:
            url = raw_url

        if is_image:
            result.append(f'<img src="{url}" alt="{alt_or_text}" loading="lazy">')
        else:
            result.append(f'<a href="{url}">{alt_or_text}</a>')

        pos = match.end()

    # 添加剩余文本
    result.append(text[pos:])
    return ''.join(result)


def md_to_html(md_text, is_gallery=False, gallery_dir=None):
    """简易 Markdown 转 HTML"""
    lines = md_text.split('\n')
    html_lines = []
    in_list = False

    for line in lines:
        stripped = line.strip()

        # 标题
        if stripped.startswith('# '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h1>{stripped[2:]}</h1>')
        elif stripped.startswith('## '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h2>{stripped[3:]}</h2>')
        elif stripped.startswith('### '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h3>{stripped[4:]}</h3>')
        # 列表项
        elif stripped.startswith('- ') or stripped.startswith('* '):
            if not in_list:
                html_lines.append('<ul>')
                in_list = True
            item = stripped[2:]
            # 处理链接和图片
            item = parse_markdown_links(item)
            html_lines.append(f'<li>{item}</li>')
        # 图片行 ![alt](<url>)
        elif stripped.startswith('!['):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            # 处理图片
            img_html = parse_markdown_links(stripped)
            html_lines.append(f'<p>{img_html}</p>')
        # 链接行 [text](<url>)
        elif stripped.startswith('[') and '](' in stripped:
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            link_html = parse_markdown_links(stripped)
            html_lines.append(f'<p>{link_html}</p>')
        # 空行
        elif stripped == '':
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append('')
        # 普通段落
        else:
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            line_processed = parse_markdown_links(stripped)
            html_lines.append(f'<p>{line_processed}</p>')

    if in_list:
        html_lines.append('</ul>')

    return '\n'.join(html_lines)


def wrap_html(title, body, layout='gallery'):
    """包装成完整 HTML 页面"""
    if layout == 'home':
        extra_style = """
        .gallery-list a {
            display: inline-block;
            margin: 8px 12px 8px 0;
            padding: 10px 16px;
            background: #1a1a2e;
            border: 1px solid #2a2a4a;
            border-radius: 8px;
            color: #e0e0e0;
            font-size: 0.9em;
            transition: all 0.2s;
        }
        .gallery-list a:hover {
            background: #2a2a4a;
            border-color: #6ec6ff;
            text-decoration: none;
            transform: translateY(-2px);
        }
        .gallery-list ul { list-style: none; padding: 0; }
        .gallery-list li { margin-bottom: 4px; }
        """
    else:
        extra_style = """
        .header {
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .back-btn {
            display: inline-block;
            padding: 8px 16px;
            background: #1a1a2e;
            border: 1px solid #2a2a4a;
            border-radius: 8px;
            color: #6ec6ff;
            font-size: 0.9em;
            transition: all 0.2s;
        }
        .back-btn:hover {
            background: #2a2a4a;
            text-decoration: none;
        }
        .image-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 12px;
        }
        .image-grid img {
            width: 100%;
            height: auto;
            border-radius: 8px;
            cursor: pointer;
            transition: transform 0.2s, opacity 0.3s;
        }
        .image-grid img:hover {
            transform: scale(1.03);
        }
        .image-grid p { margin: 0; }
        .lightbox {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.95);
            z-index: 9999;
            justify-content: center;
            align-items: center;
            cursor: pointer;
        }
        .lightbox img {
            max-width: 95%;
            max-height: 95%;
            border-radius: 4px;
        }
        .lightbox.active { display: flex; }
        """

    back_btn = '<a href="/蠢沫沫.html" class="back-btn">← 返回列表</a>' if layout == 'gallery' else ''

    if layout == 'gallery':
        lightbox_html = '<div class="lightbox" onclick="this.classList.remove(\'active\')"><img></div><script>var lb=document.querySelector(".lightbox");document.querySelectorAll(".image-grid img").forEach(function(img){img.onclick=function(){lb.querySelector("img").src=this.src;lb.classList.add("active")}})</script>'
    else:
        lightbox_html = ''

    content_class = 'gallery-list' if layout == 'home' else 'image-grid'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans CJK SC", sans-serif;
      background: #0f0f0f;
      color: #e0e0e0;
      line-height: 1.6;
    }}
    a {{ color: #6ec6ff; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
    h1 {{ font-size: 1.8em; margin-bottom: 20px; }}
    .disclaimer {{
      background: #1a1a2e;
      border-left: 3px solid #e74c3c;
      padding: 12px 16px;
      margin-bottom: 24px;
      border-radius: 4px;
      font-size: 0.9em;
      color: #aaa;
    }}
    {extra_style}
  </style>
</head>
<body>
  <div class="container">
    {back_btn}
    <h1>{title}</h1>
    <div class="disclaimer">
      此仓库仅供学习和交流使用，请在下载后 24 小时内删除！
    </div>
    <div class="{content_class}">
      {body}
    </div>
  </div>
  {lightbox_html}
</body>
</html>"""


def fix_links_for_home(html_body):
    """修正主页链接：将 蠢沫沫/xxx 改为 xxx.html"""
    # 匹配 href="蠢沫沫/xxx" 并改为 href="xxx.html"
    def replace_link(match):
        url = match.group(1)
        # 去掉 蠢沫沫/ 前缀
        if url.startswith('蠢沫沫/'):
            url = url[len('蠢沫沫/'):]
        # 加 .html 后缀
        if not url.endswith('.html') and not url.endswith('/'):
            url = url + '.html'
        # URL 编码
        return f'href="{encode_url(url)}"'

    return re.sub(r'href="([^"]+)"', replace_link, html_body)


def fix_images_for_gallery(html_body):
    """修正画廊页图片路径：加上 蠢沫沫/ 前缀"""
    # 匹配 src="xxx/xxx.webp" 并改为 src="蠢沫沫/xxx/xxx.webp"
    def replace_img(match):
        url = match.group(1)
        # 如果已经是完整 URL，不改
        if url.startswith('http://') or url.startswith('https://'):
            return f'src="{url}"'
        # 如果已经有 蠢沫沫/ 前缀，不改
        if url.startswith('蠢沫沫/'):
            return f'src="{url}"'
        # 加上 蠢沫沫/ 前缀
        full_url = '蠢沫沫/' + url
        return f'src="{encode_url(full_url)}"'

    return re.sub(r'src="([^"]+)"', replace_img, html_body)


def process_md(filepath, output_dir, is_home=False):
    """处理单个 .md 文件"""
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    # 去掉 BOM
    if content.startswith('\ufeff'):
        content = content[1:]

    # 去掉 front matter
    if content.startswith('---'):
        end = content.find('---', 3)
        if end != -1:
            content = content[end + 3:].lstrip()

    # 提取标题
    title_match = re.match(r'^#\s+(.+)', content.strip())
    title = title_match.group(1) if title_match else os.path.splitext(os.path.basename(filepath))[0]

    body = md_to_html(content)

    # 修正链接和图片路径
    if is_home:
        body = fix_links_for_home(body)
    else:
        body = fix_images_for_gallery(body)

    layout = 'home' if is_home else 'gallery'
    html_content = wrap_html(title, body, layout)

    # 输出文件名
    basename = os.path.basename(filepath)
    html_name = os.path.splitext(basename)[0] + '.html'

    output_path = os.path.join(output_dir, html_name)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return html_name


def copy_assets(root, output):
    """复制非 .md 文件（图片等）到输出目录"""
    for dirpath, dirnames, filenames in os.walk(root):
        # 跳过 .git 和 _site 和 _layouts
        if '.git' in dirpath or '_site' in dirpath or '_layouts' in dirpath:
            continue

        for filename in filenames:
            if filename.endswith('.md') or filename.endswith('.py') or filename == 'Gemfile' or filename == '_config.yml' or filename == '.python-version':
                continue

            src_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(src_path, root)
            dst_path = os.path.join(output, rel_path)

            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            shutil.copy2(src_path, dst_path)


def main():
    root = ROOT
    output = OUTPUT

    # 清理输出目录
    if os.path.exists(output):
        shutil.rmtree(output)
    os.makedirs(output)

    # 处理主页
    main_md = os.path.join(root, '蠢沫沫.md')
    if os.path.exists(main_md):
        process_md(main_md, output, is_home=True)
        print(f"  主页: 蠢沫沫.html")

    # 处理蠢沫沫/目录下所有 .md 文件
    gallery_dir = os.path.join(root, '蠢沫沫')
    count = 0
    if os.path.isdir(gallery_dir):
        for md_file in sorted(glob.glob(os.path.join(gallery_dir, '*.md'))):
            process_md(md_file, output)
            count += 1

    # 复制图片等资源
    copy_assets(root, output)

    # 创建 index.html 重定向
    index_path = os.path.join(output, 'index.html')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write("""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="0; url=/蠢沫沫.html">
  <title>蠢沫沫作品集</title>
  <script>location.href = '/蠢沫沫.html';</script>
</head>
<body>
  <p>正在跳转... <a href="/蠢沫沫.html">点击这里</a></p>
</body>
</html>""")

    print(f"完成！共处理 {count} 个作品集 + 1 个主页")
    print(f"输出目录: {output}")


if __name__ == '__main__':
    main()
