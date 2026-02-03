# -*- coding: utf-8 -*-
import argparse
import json
import os
from jinja2 import Environment, FileSystemLoader, select_autoescape

try:
    from weasyprint import HTML, CSS
except Exception:
    HTML = None


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def render_html(data, templates_dir):
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(['html', 'xml'])
    )
    template = env.get_template('resume.html')
    return template.render(data=data)


def html_to_pdf(html_string, output_path, base_url=None):
    if HTML is None:
        raise RuntimeError('WeasyPrint is not installed. Install dependencies from requirements.txt')
    HTML(string=html_string, base_url=base_url).write_pdf(output_path)


def write_html_file(html_string, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_string)


def main():
    parser = argparse.ArgumentParser(description='Generate a PDF (or HTML) resume from JSON using a template')
    parser.add_argument('input', help='Path to JSON input file')
    parser.add_argument('--output', '-o', default='resume.pdf', help='Output file path (PDF or HTML)')
    parser.add_argument('--templates', '-t', default='templates', help='Templates directory')
    parser.add_argument('--html-only', action='store_true', help='Write HTML output instead of converting to PDF')
    args = parser.parse_args()

    data = load_json(args.input)

    # render HTML
    html = render_html(data, args.templates)

    base_url = os.path.abspath(args.templates)

    if args.html_only:
        out = args.output
        if not out.lower().endswith('.html'):
            out = os.path.splitext(out)[0] + '.html'
        write_html_file(html, out)
        print(f'Generated HTML: {out} (open in browser and print to PDF)')
        return

    # convert to PDF (requires WeasyPrint native deps)
    if HTML is None:
        raise RuntimeError('WeasyPrint native libraries are missing. Use --html-only to generate HTML or install native deps.')

    html_to_pdf(html, args.output, base_url=base_url)
    print(f'Generated PDF: {args.output}')


if __name__ == '__main__':
    main()
