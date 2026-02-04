# Resume Generator

This tool generates a clean PDF resume from a JSON file using a Jinja2 HTML template and multiple PDF renderers (WeasyPrint and Playwright).

Requirements

- Python 3.8+
- Install dependencies:

```bash
pip install -r requirements.txt
```

If you want fully headerless PDFs on Windows, install Playwright browsers:

```bash
python -m playwright install
```

On Windows you may need additional system dependencies for WeasyPrint (cairo, pango). See WeasyPrint docs: https://weasyprint.org/docs/
If WeasyPrint is unavailable, the script will use Playwright (if installed) or fall back to headless Chrome/Edge.

Usage

```bash
python generate_resume.py sample_input.json --output my_resume.pdf
```

React UI

Start the API server (serves the React UI and PDF endpoint):

```bash
pip install -r requirements.txt
python -m playwright install
python -m uvicorn api_server:app --reload
```

Open http://127.0.0.1:8000 in your browser, paste text, and click Download PDF.

Text-to-JSON helper

If you have plain text like in inputdata.txt, convert it to JSON:

```bash
python parse_input_text.py inputdata.txt --output sample_input.json
```

Files

- `generate_resume.py` - main script
- `templates/resume.html` - HTML template
- `sample_input.json` - example JSON input

Customize the template in `templates/resume.html` for different visual styles or fonts.

HTML-only mode

If installing WeasyPrint native libraries is difficult on Windows, generate an HTML file and print to PDF from your browser:

```bash
python generate_resume.py sample_input.json --html-only --output resume.html
# Open resume.html in your browser, then Print -> Save as PDF
```
