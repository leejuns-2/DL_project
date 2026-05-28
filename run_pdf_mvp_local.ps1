$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot
python -m streamlit run app_pdf_mvp.py --server.port 8501 --server.headless true
