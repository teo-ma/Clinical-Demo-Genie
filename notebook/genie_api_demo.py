# Databricks notebook source
# MAGIC %md
# MAGIC # Genie Conversation API 演示
# MAGIC
# MAGIC 演示如何用 **Python + REST API** 调用 Genie Space，从而把 Genie 嵌入到任意应用 / 后端。
# MAGIC
# MAGIC API 文档：<https://docs.databricks.com/api/azure/workspace/genie>
# MAGIC
# MAGIC **流程**：
# MAGIC 1. `POST /api/2.0/genie/spaces/{space_id}/start-conversation` —— 启动会话并发首条消息
# MAGIC 2. 轮询 `GET .../conversations/{conv_id}/messages/{msg_id}` 直到 `status = COMPLETED`
# MAGIC 3. `GET .../messages/{msg_id}/query-result` —— 拉取生成的 SQL 与查询结果
# MAGIC 4. 后续追问用 `POST .../conversations/{conv_id}/messages`

# COMMAND ----------
# MAGIC %md ## 配置

# COMMAND ----------

# 在 Databricks Notebook 内运行时，下面两个变量可自动获取
DATABRICKS_HOST = (
    dbutils.notebook.entry_point.getDbutils().notebook().getContext()
        .apiUrl().getOrElse(None)
)
DATABRICKS_TOKEN = (
    dbutils.notebook.entry_point.getDbutils().notebook().getContext()
        .apiToken().getOrElse(None)
)

# Genie Space ID
SPACE_ID = "01f1490141e91adda521c7b6eef2df6a"

print("Host:", DATABRICKS_HOST)
print("Space:", SPACE_ID)

# COMMAND ----------
# MAGIC %md ## API 客户端

# COMMAND ----------

import time, requests, json
from typing import Optional

class GenieClient:
    def __init__(self, host: str, token: str, space_id: str):
        self.base = f"{host.rstrip('/')}/api/2.0/genie/spaces/{space_id}"
        self.h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        self.conversation_id: Optional[str] = None

    def _wait(self, conv_id: str, msg_id: str, timeout: int = 120) -> dict:
        url = f"{self.base}/conversations/{conv_id}/messages/{msg_id}"
        deadline = time.time() + timeout
        while time.time() < deadline:
            r = requests.get(url, headers=self.h, timeout=30); r.raise_for_status()
            m = r.json()
            if m.get("status") in ("COMPLETED", "FAILED", "CANCELLED"):
                return m
            time.sleep(2)
        raise TimeoutError(f"Genie message {msg_id} timed out")

    def ask(self, question: str) -> dict:
        if self.conversation_id is None:
            url = f"{self.base}/start-conversation"
            r = requests.post(url, headers=self.h, json={"content": question}, timeout=30)
        else:
            url = f"{self.base}/conversations/{self.conversation_id}/messages"
            r = requests.post(url, headers=self.h, json={"content": question}, timeout=30)
        r.raise_for_status()
        body = r.json()
        if "conversation_id" in body:
            self.conversation_id = body["conversation_id"]
            msg_id = body["message_id"]
        else:
            msg_id = body["id"]
        msg = self._wait(self.conversation_id, msg_id)
        # 拉取 query 结果（如果生成了 SQL）
        result = None
        for attachment in msg.get("attachments", []) or []:
            if attachment.get("query"):
                qr_url = f"{self.base}/conversations/{self.conversation_id}/messages/{msg_id}/query-result/{attachment['attachment_id']}"
                qr = requests.get(qr_url, headers=self.h, timeout=30)
                if qr.ok:
                    result = qr.json()
                break
        return {"message": msg, "result": result}

# COMMAND ----------
# MAGIC %md ## 演示：单轮提问

# COMMAND ----------

genie = GenieClient(DATABRICKS_HOST, DATABRICKS_TOKEN, SPACE_ID)

resp = genie.ask("当前在组的受试者总数？按试验分组列出。")
print("生成的 SQL:")
for att in resp["message"].get("attachments", []) or []:
    if att.get("query"):
        print(att["query"].get("query"))
print("\n回答文本:")
for att in resp["message"].get("attachments", []) or []:
    if att.get("text"):
        print(att["text"].get("content"))

# COMMAND ----------
# MAGIC %md ## 演示：多轮追问（使用同一 conversation_id）

# COMMAND ----------

resp2 = genie.ask("其中入组完成度最高的 3 个试验是哪些？")
print(json.dumps(resp2["message"], indent=2, ensure_ascii=False)[:2000])

# COMMAND ----------
# MAGIC %md ## 演示：把结果转为 DataFrame

# COMMAND ----------

import pandas as pd

def result_to_pandas(result_json: dict) -> pd.DataFrame:
    if not result_json:
        return pd.DataFrame()
    sr = result_json.get("statement_response", result_json)
    manifest = sr.get("manifest", {})
    cols = [c["name"] for c in manifest.get("schema", {}).get("columns", [])]
    rows = (sr.get("result", {}) or {}).get("data_array", []) or []
    return pd.DataFrame(rows, columns=cols)

df = result_to_pandas(resp["result"])
display(df)
