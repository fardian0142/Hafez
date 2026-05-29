import orjson
from pathlib import Path
from datetime import datetime

DATA_DIR = Path("data")

results = orjson.loads((DATA_DIR / "results.json").read_bytes())

html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Arista CDN Scanner</title>
<style>
body {{
    background:#0f172a;
    color:white;
    font-family:Arial;
    padding:40px;
}}
table {{
    width:100%;
    border-collapse:collapse;
    margin-bottom:40px;
}}
th,td {{
    border:1px solid #334155;
    padding:12px;
}}
th {{
    background:#1e293b;
}}
tr:nth-child(even) {{
    background:#111827;
}}
h1,h2 {{
    color:#38bdf8;
}}
</style>
</head>
<body>
<h1>Arista CDN Scanner</h1>
<p>Last Update: {datetime.utcnow().isoformat()} UTC</p>
"""

for port, items in results.items():
    html += f"<h2>Port {port}</h2>"
    html += """
    <table>
    <tr>
    <th>IP</th>
    <th>Latency</th>
    <th>SNI</th>
    </tr>
    """

    for item in items:
        html += f"""
        <tr>
        <td>{item['ip']}</td>
        <td>{item['latency']} ms</td>
        <td>{item['sni']}</td>
        </tr>
        """

    html += "</table>"

html += "</body></html>"

(Path("index.html")).write_text(html)

clash = []

for port, items in results.items():
    for item in items:
        clash.append(
            {
                "name": f"{item['ip']}:{port}",
                "server": item["ip"],
                "port": int(port),
                "type": "trojan",
                "sni": item["sni"],
                "skip-cert-verify": True
            }
        )

(Path("data/clash.json")).write_bytes(orjson.dumps(clash))

xray = []

for port, items in results.items():
    for item in items:
        xray.append(
            {
                "address": item["ip"],
                "port": int(port),
                "sni": item["sni"]
            }
        )

(Path("data/xray.json")).write_bytes(orjson.dumps(xray))
