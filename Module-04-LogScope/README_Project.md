# LogScope – JSON Log Analyzer

B.Tech CSE Mini Project | Academic Year 2026–27  
Faculty Guide: Ms. Sujithra G

## Team
- Danah Raj K – 25BTRPW029
- Arpita Biswal – 25BTRPW018
- Divyanshu Nahata – 25BTRPW035
- Ananya Guddad – 25BTRPW013

## Technology Stack
Python, JSON, Pandas, Streamlit and Plotly.

## Features
JSON/JSONL upload, record validation, severity KPIs, error and critical rates,
repeated-error alerts, service error-rate alerts, filters, keyword search,
activity/severity/service charts, CSV export and JSON report export.

## Required JSON fields
`timestamp`, `level`, `service`, `message`. Optional: `source`.
Severity must be INFO, WARNING, ERROR or CRITICAL.

## Run the application
1. Install Python 3.10 or later.
2. Open a terminal in this folder.
3. Run `pip install -r requirements.txt`.
4. Run `streamlit run app.py`.
5. Open the localhost URL shown in the terminal (normally http://localhost:8501).

## Sample dataset
`sample_logs.json` contains 100 demonstration records: INFO 53, WARNING 21,
ERROR 21, CRITICAL 5; error rate 21%, critical rate 5%, and three repeated
error message patterns at a threshold of 3. These are sample figures, not
production benchmarks.

## Limitations
The analysis is rule-based and depends on input quality. It identifies issues
but does not automatically fix them. Real-time streaming, ML anomaly detection,
cloud monitoring and email notifications are future enhancements.
