#!/usr/bin/env bash
# 用法: ./scripts/ask_genie.sh "你的问题"
# 演示：用 Databricks CLI 完成一次 Genie 自然语言问答 + 取数据
set -e

SPACE_ID="${SPACE_ID:-01f1490141e91adda521c7b6eef2df6a}"
QUESTION="${1:?用法: $0 \"问题\"}"

echo "===== 提问: $QUESTION ====="
TMP=$(mktemp /tmp/genie.XXXXXX.json)
databricks genie start-conversation -o json "$SPACE_ID" "$QUESTION" > "$TMP"

python3 - "$TMP" "$SPACE_ID" <<'PY'
import json, sys, subprocess
path, space_id = sys.argv[1], sys.argv[2]
with open(path) as f:
    r = json.load(f)

conv_id = r["conversation_id"]
msg_id = r["message_id"]
print(f"\nconversation_id: {conv_id}")
print(f"message_id:      {msg_id}")

att_query = None
for a in r["attachments"]:
    if "text" in a:
        print("\n=== 文字回答 ===")
        print(a["text"]["content"])
    if "query" in a:
        att_query = a
        print("\n=== 生成的 SQL ===")
        print(a["query"]["query"])

if att_query:
    print("\n=== 数据行 ===")
    out = subprocess.check_output([
        "databricks", "genie", "get-message-attachment-query-result",
        "-o", "json", space_id, conv_id, msg_id, att_query["attachment_id"],
    ])
    data = json.loads(out)
    cols = [c["name"] for c in data["statement_response"]["manifest"]["schema"]["columns"]]
    rows = data["statement_response"]["result"].get("data_array") or []
    print(" | ".join(cols))
    print("-" * 60)
    for row in rows:
        print(" | ".join(str(v) for v in row))

print(f"\n💡 想追问？运行:")
print(f'   databricks genie create-message {space_id} {conv_id} "你的追问"')
PY
rm -f "$TMP"
