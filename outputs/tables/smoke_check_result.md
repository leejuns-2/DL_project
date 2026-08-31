# Smoke Check Result

- status: `pass`
- generated_at_utc: `2026-08-31T10:48:26.230430+00:00`

| Status | Check |
|---|---|
| pass | FastAPI app imports |
| pass | dashboard API returns 200 |
| pass | dashboard API includes methodology |
| pass | dashboard methodology names MiniLM |
| pass | web app root returns 200 |
| pass | event window returns are generated |
| pass | abnormal return column exists |
| pass | non-energy text is marked out_of_domain |
| skip | sample energy PDF check requires scripts/download_validation_pdfs.py |
| pass | split metrics include all groups |
| pass | close high-confidence themes are marked mixed_signal |
| pass | mixed signal keeps renewable component visible |
| pass | mixed signal keeps fossil component visible |
| pass | chunk weak labels can mark multi-label evidence |
| pass | chunk label summary counts mixed chunks |
| pass | summary support metadata includes evidence chunk ids |
