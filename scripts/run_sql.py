#!/usr/bin/env python3
"""Run a multi-statement SQL file against a Databricks SQL Warehouse via Statement Execution API.

Auth: uses DATABRICKS_HOST + AAD via az CLI (DATABRICKS_AZURE_RESOURCE_ID).
"""
import json, os, re, subprocess, sys, time, urllib.request

HOST = os.environ["DATABRICKS_HOST"].rstrip("/")
WH = os.environ["WAREHOUSE_ID"]
SQL_FILE = sys.argv[1]

def get_token():
    out = subprocess.check_output([
        "az", "account", "get-access-token",
        "--resource", "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d",
        "-o", "json",
    ])
    return json.loads(out)["accessToken"]

TOKEN = get_token()

def api(path, body=None, method="POST"):
    req = urllib.request.Request(
        f"{HOST}{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())

def split_sql(text: str):
    # 去掉 -- 注释
    text = re.sub(r"--[^\n]*", "", text)
    parts = [s.strip() for s in text.split(";")]
    return [p for p in parts if p]

with open(SQL_FILE) as f:
    statements = split_sql(f.read())

print(f"Running {len(statements)} statements from {SQL_FILE}")
CATALOG = os.environ.get("DEFAULT_CATALOG")
SCHEMA = os.environ.get("DEFAULT_SCHEMA")

for i, stmt in enumerate(statements, 1):
    head = stmt[:80].replace("\n", " ")
    # Skip USE statements — pass catalog/schema as request fields instead.
    if re.match(r"^\s*USE\s+(CATALOG|SCHEMA)\s+", stmt, re.IGNORECASE):
        print(f"[{i}/{len(statements)}] SKIP (handled via request fields): {head}")
        continue
    body = {"warehouse_id": WH, "statement": stmt, "wait_timeout": "50s"}
    if CATALOG:
        body["catalog"] = CATALOG
    if SCHEMA:
        body["schema"] = SCHEMA
    r = api("/api/2.0/sql/statements", body)
    state = r.get("status", {}).get("state")
    sid = r.get("statement_id")
    while state in ("PENDING", "RUNNING"):
        time.sleep(2)
        r = api(f"/api/2.0/sql/statements/{sid}", method="GET")
        state = r.get("status", {}).get("state")
    if state != "SUCCEEDED":
        err = r.get("status", {}).get("error", {})
        print(f"[{i}/{len(statements)}] FAIL: {head}\n  -> {err}")
        sys.exit(2)
    print(f"[{i}/{len(statements)}] OK: {head}")

print("All statements succeeded.")
