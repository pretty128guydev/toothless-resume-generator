#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import io
import tempfile
from pathlib import Path
import asyncio
import sys

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse

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


@app.get('/', response_class=HTMLResponse)
def index():
    return UI_INDEX.read_text(encoding='utf-8')


@app.post('/api/generate')
async def generate(request: Request):
    payload = await request.json()
    text = (payload or {}).get('text', '')
    if not text.strip():
        raise HTTPException(status_code=400, detail='Empty text')

    data = parse_text(text)
    html = render_html(data, str(TEMPLATES_DIR))

    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        pdf_path = Path(tmp.name)

    await asyncio.to_thread(html_to_pdf, html, str(pdf_path), base_url=str(TEMPLATES_DIR))

    pdf_bytes = pdf_path.read_bytes()
    pdf_path.unlink(missing_ok=True)

    return StreamingResponse(io.BytesIO(pdf_bytes), media_type='application/pdf', headers={
        'Content-Disposition': 'attachment; filename="resume.pdf"'
    })
