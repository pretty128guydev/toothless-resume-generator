#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

try:
    from weasyprint import HTML
except Exception:
    HTML = None

try:
    import websocket
except Exception:
    websocket = None

import urllib.request
import urllib.parse
import json as _json
import base64


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def render_html(data, templates_dir):
    env = Environment(loader=FileSystemLoader(templates_dir), autoescape=select_autoescape(['html', 'xml']))
    template = env.get_template('resume.html')
    return template.render(data=data)


def _try_print_to_pdf_with_chrome(bin_path, file_uri, output_path):
    cmd = [bin_path, '--headless=new', '--disable-gpu', '--no-sandbox', f'--print-to-pdf={os.path.abspath(output_path)}', '--print-to-pdf-no-header', file_uri]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _cdp_print(page_url, output_path, bin_path, tmp_html):
    user_data = tempfile.mkdtemp(prefix='chrome-user-')
    proc = subprocess.Popen([bin_path, '--remote-debugging-port=9222', f'--user-data-dir={user_data}', '--no-first-run', '--no-default-browser-check', '--headless=new', '--disable-gpu', '--no-sandbox'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    server_dir = tempfile.mkdtemp(prefix='htmlserver-')
    serve_name = 'resume_temp.html'
    shutil.copy(tmp_html, os.path.join(server_dir, serve_name))

    import socket
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()

    server_proc = subprocess.Popen(["python", '-m', 'http.server', str(port), '--bind', '127.0.0.1'], cwd=server_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    served_url = f'http://127.0.0.1:{port}/{serve_name}'

    info = None
    deadline = time.time() + 8
    while time.time() < deadline:
        try:
            q = urllib.parse.quote(served_url, safe=':/?&=')
            with urllib.request.urlopen('http://127.0.0.1:9222/json/new?' + q) as r:
                info = _json.loads(r.read().decode('utf-8'))
            if info and info.get('webSocketDebuggerUrl'):
                break
        except Exception:
            time.sleep(0.25)

    if not info or not info.get('webSocketDebuggerUrl'):
        try:
            proc.terminate()
        except Exception:
            pass
        try:
            server_proc.terminate()
        except Exception:
            pass
        return False

    ws_url = info.get('webSocketDebuggerUrl')
    ws = websocket.create_connection(ws_url, timeout=10)

    ws.send(_json.dumps({'id': 1, 'method': 'Page.enable'}))
    ws.send(_json.dumps({'id': 2, 'method': 'Page.navigate', 'params': {'url': served_url}}))

    deadline = time.time() + 12
    while time.time() < deadline:
        try:
            resp = ws.recv()
        except Exception:
            break
        if not resp:
            continue
        rj = _json.loads(resp)
        if rj.get('method') == 'Page.loadEventFired':
            break

    msg = {'id': 3, 'method': 'Page.printToPDF', 'params': {'printBackground': True, 'displayHeaderFooter': False, 'paperWidth': 8.27, 'paperHeight': 11.69, 'marginTop': 0.4, 'marginBottom': 0.4, 'marginLeft': 0.4, 'marginRight': 0.4}}
    ws.send(_json.dumps(msg))

    pdf_data = None
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            resp = ws.recv()
        except Exception:
            break
        if not resp:
            continue
        respj = _json.loads(resp)
        if respj.get('id') == 3 and 'result' in respj:
            pdf_data = respj['result'].get('data')
            break

    ws.close()
    if pdf_data:
        with open(output_path, 'wb') as outf:
            outf.write(base64.b64decode(pdf_data))
        try:
            urllib.request.urlopen('http://127.0.0.1:9222/json/close/' + info.get('id',''))
        except Exception:
            pass
        try:
            proc.terminate()
        except Exception:
            pass
        try:
            proc.wait(timeout=3)
        except Exception:
            pass
        try:
            server_proc.terminate()
        except Exception:
            pass
        try:
            server_proc.wait(timeout=3)
        except Exception:
            pass
        return True

    try:
        proc.terminate()
    except Exception:
        pass
    try:
        server_proc.terminate()
    except Exception:
        pass
    return False


def html_to_pdf(html_string, output_path, base_url=None, browser_path=None):
    if HTML is not None:
        try:
            HTML(string=html_string, base_url=base_url).write_pdf(output_path)
            return
        except Exception as e:
            print('WeasyPrint failed:', e)

    fd, tmp_html = tempfile.mkstemp(suffix='.html')
    os.close(fd)
    with open(tmp_html, 'w', encoding='utf-8') as f:
        f.write(html_string)

    chrome_bins = []
    if browser_path:
        chrome_bins.append(browser_path)
    chrome_bins.extend([shutil.which('chrome'), shutil.which('google-chrome'), shutil.which('chromium'), shutil.which('chromium-browser'), shutil.which('msedge')])
    chrome_bins = [p for p in chrome_bins if p]
    if os.name == 'nt':
        common = [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Chromium\Application\chrome.exe"]
        for p in common:
            if p not in chrome_bins and os.path.exists(p):
                chrome_bins.append(p)

    if not chrome_bins:
        os.remove(tmp_html)
        raise RuntimeError('No PDF renderer available (WeasyPrint missing and no Chrome/Edge found). Use --html-only.')

    file_uri = Path(tmp_html).resolve().as_uri()
    for bin_path in chrome_bins:
        # Prefer CDP-based print (can disable headers reliably)
        if websocket is not None:
            try:
                ok = _cdp_print(file_uri, output_path, bin_path, tmp_html)
                if ok:
                    print(f'Printed via CDP using {bin_path}')
                    try:
                        os.remove(tmp_html)
                    except Exception:
                        pass
                    return
            except Exception:
                print(f'CDP print failed for {bin_path}:', sys.exc_info()[0])
                pass

        # Fallback: direct --print-to-pdf (may include headers on some builds)
        try:
            _try_print_to_pdf_with_chrome(bin_path, file_uri, output_path)
            print(f'Printed via direct --print-to-pdf using {bin_path}')
            os.remove(tmp_html)
            return
        except Exception:
            print(f'direct print failed for {bin_path}:', sys.exc_info()[0])
            continue

    try:
        os.remove(tmp_html)
    except Exception:
        pass
    raise RuntimeError('Failed to render PDF with available browsers. Use --html-only to produce HTML.')


def write_html_file(html_string, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_string)


def main():
    parser = argparse.ArgumentParser(description='Generate a PDF (or HTML) resume from JSON using a template')
    parser.add_argument('input', help='Path to JSON input file')
    parser.add_argument('--output', '-o', default='resume.pdf', help='Output file path (PDF or HTML)')
    parser.add_argument('--templates', '-t', default='templates', help='Templates directory')
    parser.add_argument('--html-only', action='store_true', help='Write HTML output instead of converting to PDF')
    parser.add_argument('--browser', '-b', help='Path to Chrome/Edge executable to use as fallback renderer')
    args = parser.parse_args()

    data = load_json(args.input)

    html = render_html(data, args.templates)

    base_url = os.path.abspath(args.templates)

    if args.html_only:
        out = args.output
        if not out.lower().endswith('.html'):
            out = os.path.splitext(out)[0] + '.html'
        write_html_file(html, out)
        print(f'Generated HTML: {out} (open in browser and print to PDF)')
        return

    html_to_pdf(html, args.output, base_url=base_url, browser_path=args.browser)
    print(f'Generated PDF: {args.output}')


if __name__ == '__main__':
    main()
