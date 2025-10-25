# Regulatory Navigator — MVP

This repository contains a prototype MVP for a Regulatory Readiness Evaluator targeted at fintech startups. The application accepts startup documents (or pasted text), extracts structured facts using a light NLP extractor, runs a rule-driven gap analysis against configurable regulatory checks, computes a weighted readiness score, and returns mapped resources and regulatory text for transparency.

## Quick start (Windows PowerShell)

1. Create and activate a Python virtual environment (recommended):

```powershell
python -m venv venv; .\venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

3. Download spaCy model (if not already installed):

```powershell
python -m spacy download en_core_web_sm
```

4. Start the Flask dev server:

```powershell
python app.py
```

The demo UI will be available at http://127.0.0.1:5000/

## API Endpoints

- `GET /api/status` — Health check
- `POST /api/map_startup_data` — Run extraction against provided JSON `{ "documents": "..." }` and return extracted fields
- `POST /api/scorecard` — Run extraction, gap analysis, scoring, and recommendations. Returns readiness score, failed gaps, score breakdown, and recommendations.
- `POST /api/scorecard_upload` — Upload one or more files (PDF/DOCX/TXT) via multipart/form-data under field `files`; the server extracts text and returns the same scorecard payload.
- `GET /api/regulation_texts` — Returns original regulation article texts used in the transparency view.
- `POST /api/report` — Generate and download a PDF report for the provided `documents` text (falls back to the demo text if omitted).
- `GET /api/assessments` — List recent assessments stored in SQLite (id, created_at, readiness_score).
- `GET /api/assessments/:id` — Get a single stored assessment payload by id.

## Tests

Run unit tests with pytest:

```powershell
python -m pytest -q
```

## Notes and limitations

- The extractor is intended for demo/testing and uses heuristics and small spaCy models; treat output as suggestions.
- `rules_config.json` contains the specialist rules and `SECTION_WEIGHTS`. Edit this JSON to change thresholds or section weights.
- `resource_mapping_data.json` maps failed gaps to curated resources (templates, guides, and compliance experts). Expand these mappings for production.
- Assessments are stored best-effort in a local SQLite DB (`assessments.db`). For production, migrate to a managed database and add authentication.

## Development tips

- Use `scripts/internal_validation.py` to run extraction, gap analysis and scoring locally without starting the HTTP server.
- Use `scripts/test_endpoints.py` to call the running server endpoints (server must be running).
- Use `scripts/test_report.py` to generate a sample PDF report without HTTP.

## Next steps (recommended)

- Add a human-in-the-loop review UI for experts to correct extractor outputs.
- Expand CI (e.g., linting, type checks) and add release packaging.
- Improve parsing quality (PDF layout handling, scanned OCR via Tesseract) and add a background worker for long docs.


If you'd like, I can add the CI workflow or generate a PDF report export for scorecards next.
