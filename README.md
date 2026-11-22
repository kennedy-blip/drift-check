# DriftCheck

DriftCheck compares baseline and candidate data batches to detect statistical and schema drift before silent changes reach production.

## Stack
- Static, zero-build HTML/CSS/ES modules in `public/`
- Python 3.12 Vercel Functions in `api/`
- Standard-library-only backend; no Node runtime or TypeScript

## Local development
Run the API and static site together with Vercel CLI:

```bash
python3 -m pip install -r requirements.txt
npm install --global vercel
vercel dev
```

Open the local URL printed by Vercel. The UI also includes a browser-only fallback analyzer when served without the Python API.

## API
- `GET /api/datasets` — seeded and process-local saved snapshots
- `POST /api/datasets` — validate and save a snapshot in the current function instance
- `POST /api/analyze` — compare records and return field-level diagnostics

> Serverless memory is ephemeral and may be isolated between invocations. The in-memory dataset endpoint is intended for demos; use a durable database or object store for persistent multi-instance snapshots.

## Drift scoring
The analyzer evaluates numeric mean shifts, population standard-deviation changes, null-rate changes, numeric range violations, categorical distribution shifts, and unseen categories. Scores are severity-weighted and normalized to 0–100. Configure the Z-score and null-rate thresholds in the UI.

## Deploy
Import `kennedy-blip/drift-check` into Vercel. No build command or Node bundler is required. The included `vercel.json` serves `public/` and maps Python functions under `/api`.

## Verification
```bash
python3 -m py_compile api/datasets.py api/analyze.py
python3 -m json.tool vercel.json
```
