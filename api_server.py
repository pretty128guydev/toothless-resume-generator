#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import io
import tempfile
import json
from pathlib import Path
import asyncio
import sys

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from parse_input_text import parse_text
from generate_resume import render_html, html_to_pdf

if sys.platform.startswith('win'):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

app = FastAPI()
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / 'templates'
UI_INDEX = BASE_DIR / 'ui' / 'index.html'
UI_DIR = BASE_DIR / 'ui'

ALLOWED_TEMPLATES = {p.name for p in TEMPLATES_DIR.glob('*.html')}


def _safe_template_name(template_name: str) -> str:
    if not template_name:
        return 'resume.html'
    name = template_name.strip()
    if '/' in name or '\\' in name:
        return 'resume.html'
    if name not in ALLOWED_TEMPLATES:
        return 'resume.html'
    return name

app.mount('/ui', StaticFiles(directory=str(UI_DIR), html=True), name='ui')


@app.get('/', response_class=HTMLResponse)
def index():
    return UI_INDEX.read_text(encoding='utf-8')


@app.post('/api/generate')
async def generate(request: Request):
    payload = await request.json()
    text = (payload or {}).get('text', '')
    template_name = _safe_template_name((payload or {}).get('template'))
    if not text.strip():
        raise HTTPException(status_code=400, detail='Empty text')

    data = parse_text(text)
    html = render_html(data, str(TEMPLATES_DIR), template_name=template_name)

    pdf_path = BASE_DIR / 'Dmitry.pdf'

    try:
        await asyncio.to_thread(html_to_pdf, html, str(pdf_path), base_url=str(TEMPLATES_DIR))
    except Exception as e:
        raise HTTPException(status_code=409, detail='Please close the opened Dmitry.pdf and try again.') from e

    pdf_bytes = pdf_path.read_bytes()

    return StreamingResponse(io.BytesIO(pdf_bytes), media_type='application/pdf', headers={
        'Content-Disposition': 'attachment; filename="Dmitry.pdf"'
    })


@app.post('/api/preview', response_class=HTMLResponse)
async def preview(request: Request):
    payload = await request.json()
    text = (payload or {}).get('text', '')
    template_name = _safe_template_name((payload or {}).get('template'))
    if not text.strip():
        raise HTTPException(status_code=400, detail='Empty text')

    data = parse_text(text)
    html = render_html(data, str(TEMPLATES_DIR), template_name=template_name)
    return HTMLResponse(content=html)


@app.get('/api/preview-template', response_class=HTMLResponse)
def preview_template(template: str = 'resume.html'):
    template_name = _safe_template_name(template)
    sample_path = BASE_DIR / 'sample_input.json'
    if not sample_path.exists():
        raise HTTPException(status_code=404, detail='sample_input.json not found')
    data = json.loads(sample_path.read_text(encoding='utf-8'))
    html = render_html(data, str(TEMPLATES_DIR), template_name=template_name)
    return HTMLResponse(content=html)


@app.post('/api/coverletter')
async def coverletter(request: Request):
    payload = await request.json()
    text = (payload or {}).get('text', '')
    if not text.strip():
        raise HTTPException(status_code=400, detail='Empty text')

    data = parse_text(text)
    letter = '\n\n'.join(data.get('cover letter', []))
    return JSONResponse({'cover_letter': letter})
