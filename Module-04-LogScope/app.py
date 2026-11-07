import json
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="LogScope | JSON Log Analyzer", page_icon="📊", layout="wide")
LEVELS = ["INFO", "WARNING", "ERROR", "CRITICAL"]
REQUIRED = ["timestamp", "level", "service", "message"]

def sample_logs():
    """Create 100 sample records with the severity values in the project PPT."""
    levels = ["INFO"]*53 + ["WARNING"]*21 + ["ERROR"]*21 + ["CRITICAL"]*5
    errors = ["Authentication failed"]*10 + ["Payment gateway timeout"]*6 + ["Database connection failed"]*5
    other = {
        "INFO": ["Request processed successfully", "User session started", "Health check completed", "Cache refreshed"],
        "WARNING": ["Response time above expected range", "Retry attempt initiated", "Storage usage approaching limit"],
        "CRITICAL": ["Service unavailable", "Database connection pool exhausted"]
    }
    services = ["authentication", "payment", "inventory", "notification"]
    rows, e = [], 0
    for i, level in enumerate(levels):
        if level == "ERROR":
            message = errors[e]; e += 1
            service = ("authentication" if message == "Authentication failed" else
                       "payment" if message == "Payment gateway timeout" else "inventory")
        else:
            message = other[level][i % len(other[level])]
            service = services[i % len(services)]
        ts = datetime(2026, 11, 6, 8, 0) + timedelta(minutes=7*i)
        rows.append({"timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                     "level": level, "service": service, "message": message,
                     "source": f"{service}_service"})
    return rows

def read_upload(upload):
    text = upload.getvalue().decode("utf-8-sig")
    if upload.name.lower().endswith((".jsonl", ".ndjson")):
        records = []
        for n, line in enumerate(text.splitlines(), 1):
            if line.strip():
                try: records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    records.append({"__bad_line__": n, "__reason__": str(exc)})
        return records
    try:
        data = json.loads(text)
        if isinstance(data, list): return data
        if isinstance(data, dict): return [data]
        raise ValueError("JSON root must be an object or array.")
    except json.JSONDecodeError:
        # Fallback: detect newline-delimited JSON even if file extension is .json.
        records = []
        for n, line in enumerate(text.splitlines(), 1):
            if line.strip():
                try: records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    records.append({"__bad_line__": n, "__reason__": str(exc)})
        if records: return records
        raise

def validate(records):
    good, bad = [], []
    for n, item in enumerate(records, 1):
        reasons = []
        if not isinstance(item, dict):
            bad.append({"record_number": n, "reason": "Record is not a JSON object"})
            continue
        if "__bad_line__" in item:
            bad.append({"record_number": item["__bad_line__"],
                        "reason": "Invalid JSON syntax: " + item.get("__reason__", "")})
            continue
        for field in REQUIRED:
            if not isinstance(item.get(field), str) or not item[field].strip():
                reasons.append(f"Missing or empty field: {field}")
        if not reasons and item["level"].strip().upper() not in LEVELS:
            reasons.append("Invalid level; use INFO, WARNING, ERROR or CRITICAL")
        timestamp = None
        if not reasons:
            try: timestamp = pd.to_datetime(item["timestamp"], errors="raise")
            except Exception: reasons.append("Invalid timestamp")
        if reasons:
            bad.append({"record_number": n, "reason": "; ".join(reasons)})
        else:
            good.append({"timestamp": timestamp, "level": item["level"].strip().upper(),
                         "service": item["service"].strip(), "message": item["message"].strip(),
                         "source": str(item.get("source", "")).strip()})
    return (pd.DataFrame(good, columns=["timestamp","level","service","message","source"]),
            pd.DataFrame(bad, columns=["record_number","reason"]))

def analyze(df, repeat_limit, service_limit, bucket):
    counts = df["level"].value_counts().reindex(LEVELS, fill_value=0)
    total = len(df)
    repeated = (df[df.level == "ERROR"].groupby("message").size()
                .reset_index(name="occurrences")
                .query("occurrences >= @repeat_limit")
                .sort_values("occurrences", ascending=False))
    service = df.groupby("service").agg(
        total_records=("level", "size"),
        error_count=("level", lambda x: int((x == "ERROR").sum())),
        critical_count=("level", lambda x: int((x == "CRITICAL").sum()))
    ).reset_index()
    service["error_rate"] = (service.error_count / service.total_records * 100).round(2)
    breaches = service[service.error_rate >= service_limit]
    activity = df.copy()
    activity["time_bucket"] = activity.timestamp.dt.floor(bucket)
    activity = activity.groupby(["time_bucket","level"]).size().reset_index(name="records")
    return {"counts": counts, "total": total, "repeated": repeated,
            "service": service, "breaches": breaches, "activity": activity,
            "error_rate": int(counts.ERROR)/total*100 if total else 0,
            "critical_rate": int(counts.CRITICAL)/total*100 if total else 0}

def report_json(result, valid_n, invalid_n, repeat_limit, service_limit):
    report = {
        "project": "LogScope - JSON Log Analyzer",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "valid_records": valid_n, "invalid_records": invalid_n,
        "severity_counts": {x: int(result["counts"][x]) for x in LEVELS},
        "error_rate_percent": round(result["error_rate"], 2),
        "critical_rate_percent": round(result["critical_rate"], 2),
        "repeated_error_patterns": result["repeated"].to_dict("records"),
        "service_summary": result["service"].to_dict("records"),
        "configuration": {"repeated_error_threshold": repeat_limit,
                          "service_error_rate_threshold_percent": service_limit}
    }
    return json.dumps(report, indent=4, default=str).encode("utf-8")

# Sidebar input and settings
st.sidebar.title("LogScope Controls")
mode = st.sidebar.radio("Input source", ["Sample dataset", "Upload JSON / JSONL"])
if mode == "Sample dataset":
    raw, filename = sample_logs(), "Built-in sample dataset"
else:
    upload = st.sidebar.file_uploader("Upload log file", type=["json","jsonl","ndjson"])
    if upload is None:
        st.info("Upload a JSON/JSONL file or select the sample dataset in the sidebar.")
        st.stop()
    filename = upload.name
    try: raw = read_upload(upload)
    except Exception as exc:
        st.error(f"Could not parse file: {exc}")
        st.stop()

st.sidebar.divider()
st.sidebar.subheader("Analysis Settings")
repeat_limit = st.sidebar.number_input("Repeated error threshold", 2, 1000, 3)
service_limit = st.sidebar.slider("Service error-rate alert (%)", 1, 100, 20)
bucket_label = st.sidebar.selectbox("Activity time bucket", ["15 minutes","1 hour","1 day"])
bucket = {"15 minutes":"15min", "1 hour":"1h", "1 day":"1D"}[bucket_label]

valid, invalid = validate(raw)
st.title("📊 LogScope – JSON Log Analyzer")
st.caption("A Python-based dashboard that turns raw application logs into clear, searchable insights.")
st.caption(f"Input: {filename}  |  Valid: {len(valid)}  |  Invalid: {len(invalid)}")
if not invalid.empty:
    with st.expander(f"Validation details – {len(invalid)} rejected records"):
        st.warning("Invalid records are excluded from analysis.")
        st.dataframe(invalid, use_container_width=True, hide_index=True)
else:
    st.success(f"Validation completed: all {len(valid)} record(s) are valid.")
if valid.empty:
    st.error("No valid records available for analysis.")
    st.stop()

# Filters
st.sidebar.divider()
st.sidebar.subheader("Log Filters")
selected_levels = st.sidebar.multiselect("Severity", LEVELS, default=LEVELS)
service_options = sorted(valid.service.unique().tolist())
selected_services = st.sidebar.multiselect("Service", service_options, default=service_options)
keyword = st.sidebar.text_input("Search message or source")
filtered = valid[valid.level.isin(selected_levels) & valid.service.isin(selected_services)].copy()
if keyword.strip():
    filtered = filtered[
        filtered.message.str.contains(keyword, case=False, na=False) |
        filtered.source.str.contains(keyword, case=False, na=False)
    ]

result = analyze(filtered, int(repeat_limit), float(service_limit), bucket)
st.subheader("Key Performance Indicators")
a,b,c,d,e = st.columns(5)
a.metric("Filtered Records", f"{result['total']:,}")
b.metric("Errors", int(result["counts"]["ERROR"]))
c.metric("Warnings", int(result["counts"]["WARNING"]))
d.metric("Error Rate", f"{result['error_rate']:.1f}%")
e.metric("Critical Rate", f"{result['critical_rate']:.1f}%")

st.divider()
st.subheader("Incident and Anomaly Alerts")
alert_count = 0
for _, row in result["repeated"].iterrows():
    st.error(f"Repeated error: '{row['message']}' occurred {int(row['occurrences'])} times.")
    alert_count += 1
for _, row in result["breaches"].iterrows():
    st.warning(f"Service '{row['service']}' has an error rate of {row['error_rate']:.1f}%.")
    alert_count += 1
if not alert_count: st.success("No repeated-error or service-threshold alerts detected.")

st.subheader("Log Analytics and Visualization")
left, right = st.columns(2)
with left:
    st.markdown("**Log Activity Over Time**")
    if not result["activity"].empty:
        fig = px.bar(result["activity"], x="time_bucket", y="records", color="level",
                     barmode="stack", category_orders={"level": LEVELS})
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("No activity data.")
with right:
    st.markdown("**Severity Distribution**")
    severity = result["counts"].rename_axis("level").reset_index(name="records")
    severity = severity[severity.records > 0]
    if not severity.empty:
        st.plotly_chart(px.pie(severity, names="level", values="records", hole=.45),
                        use_container_width=True)
    else: st.info("No severity data.")

st.markdown("**Errors by Service**")
if not result["service"].empty:
    st.plotly_chart(px.bar(result["service"].sort_values("error_count", ascending=False),
                           x="service", y="error_count", color="error_count"),
                    use_container_width=True)

st.subheader("Repeated Error Patterns")
st.dataframe(result["repeated"], use_container_width=True, hide_index=True)
st.subheader("Service Performance Summary")
st.dataframe(result["service"], use_container_width=True, hide_index=True)
st.subheader("Log Explorer")
st.caption(f"Showing {len(filtered)} of {len(valid)} valid records after filters.")
display = filtered.sort_values("timestamp", ascending=False).copy()
display["timestamp"] = display.timestamp.dt.strftime("%Y-%m-%d %H:%M:%S")
st.dataframe(display, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Export Reports")
csv_frame = filtered.copy()
csv_frame["timestamp"] = csv_frame.timestamp.dt.strftime("%Y-%m-%d %H:%M:%S")
x,y = st.columns(2)
with x:
    st.download_button("Download filtered logs (CSV)", csv_frame.to_csv(index=False).encode("utf-8"),
                       "logscope_filtered_logs.csv", "text/csv", use_container_width=True)
with y:
    st.download_button("Download analysis report (JSON)",
                       report_json(result, len(valid), len(invalid), int(repeat_limit), float(service_limit)),
                       "logscope_analysis_report.json", "application/json", use_container_width=True)

with st.expander("About this project"):
    st.write("LogScope uses Python, JSON, Pandas, Streamlit and Plotly.")
    st.write("Required fields: timestamp, level, service and message. Optional field: source.")
