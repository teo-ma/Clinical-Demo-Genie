"""Streamlit 前端：通过 Genie Conversation API 给最终用户提供自然语言数据问答。

本地运行：
    pip install -r requirements.txt
    export DATABRICKS_HOST=https://adb-xxx.azuredatabricks.net
    export DATABRICKS_TOKEN=dapi***
    export GENIE_SPACE_ID=01ef***
    streamlit run streamlit_app.py

部署到 Databricks Apps：
    见 app.yaml；DATABRICKS_HOST/TOKEN 由平台自动注入，仅需配置 GENIE_SPACE_ID。
"""
from __future__ import annotations

import os
import time
from typing import Optional

import pandas as pd
import requests
import streamlit as st


# -----------------------------------------------------------------
# Genie API client
# -----------------------------------------------------------------
class GenieClient:
    def __init__(self, host: str, token: str, space_id: str):
        self.base = f"{host.rstrip('/')}/api/2.0/genie/spaces/{space_id}"
        self.h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def _wait(self, conv_id: str, msg_id: str, timeout: int = 180) -> dict:
        url = f"{self.base}/conversations/{conv_id}/messages/{msg_id}"
        deadline = time.time() + timeout
        while time.time() < deadline:
            r = requests.get(url, headers=self.h, timeout=30)
            r.raise_for_status()
            m = r.json()
            if m.get("status") in ("COMPLETED", "FAILED", "CANCELLED"):
                return m
            time.sleep(2)
        raise TimeoutError("Genie message timed out")

    def ask(self, question: str, conversation_id: Optional[str]) -> dict:
        if conversation_id is None:
            r = requests.post(
                f"{self.base}/start-conversation",
                headers=self.h,
                json={"content": question},
                timeout=30,
            )
        else:
            r = requests.post(
                f"{self.base}/conversations/{conversation_id}/messages",
                headers=self.h,
                json={"content": question},
                timeout=30,
            )
        r.raise_for_status()
        body = r.json()
        conv_id = body.get("conversation_id", conversation_id)
        msg_id = body.get("message_id") or body.get("id")
        msg = self._wait(conv_id, msg_id)
        result = None
        sql = None
        text = None
        for att in msg.get("attachments", []) or []:
            if att.get("query"):
                sql = att["query"].get("query")
                qr = requests.get(
                    f"{self.base}/conversations/{conv_id}/messages/{msg_id}/query-result/{att['attachment_id']}",
                    headers=self.h,
                    timeout=30,
                )
                if qr.ok:
                    result = qr.json()
            if att.get("text"):
                text = att["text"].get("content")
        return {
            "conversation_id": conv_id,
            "message_id": msg_id,
            "sql": sql,
            "text": text,
            "result": result,
            "raw": msg,
        }


def result_to_df(result_json: Optional[dict]) -> pd.DataFrame:
    if not result_json:
        return pd.DataFrame()
    sr = result_json.get("statement_response", result_json)
    cols = [c["name"] for c in sr.get("manifest", {}).get("schema", {}).get("columns", [])]
    rows = (sr.get("result", {}) or {}).get("data_array", []) or []
    df = pd.DataFrame(rows, columns=cols)
    # 尝试把数字列转 numeric
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="ignore")
    return df


# -----------------------------------------------------------------
# UI
# -----------------------------------------------------------------
st.set_page_config(page_title="Clinical Genie · 临床数据问答", page_icon="🧬", layout="wide")

st.title("🧬 Clinical Genie")
st.caption("基于 Azure Databricks AI/BI Genie 的临床试验自然语言数据问答 Demo")

HOST = os.getenv("DATABRICKS_HOST", "")
TOKEN = os.getenv("DATABRICKS_TOKEN", "")
SPACE_ID = os.getenv("GENIE_SPACE_ID", "")

with st.sidebar:
    st.subheader("连接配置")
    HOST = st.text_input("Databricks Host", HOST, placeholder="https://adb-xxx.azuredatabricks.net")
    SPACE_ID = st.text_input("Genie Space ID", SPACE_ID)
    TOKEN = st.text_input("Token", TOKEN, type="password")
    if st.button("🔄 新建会话"):
        st.session_state.pop("conv_id", None)
        st.session_state.pop("history", None)
        st.rerun()

    st.markdown("---")
    st.subheader("💡 试试这些问题")
    suggested = [
        "当前在组的受试者总数？按试验分组列出。",
        "Treatment 组和 Control 组的 SAE 发生率对比",
        "最常见的 10 种不良事件是什么？",
        "各区域每月的入组人数趋势",
        "肝功能异常受试者数量按试验分组排序",
        "受试者退出原因分布",
        "Top 10 入组数最多的研究中心",
    ]
    for q in suggested:
        if st.button(q, key=f"sg_{q}"):
            st.session_state["pending_q"] = q

if not (HOST and TOKEN and SPACE_ID):
    st.warning("请在左侧填写 Databricks Host / Space ID / Token 后开始。")
    st.stop()

if "history" not in st.session_state:
    st.session_state.history = []  # list of (role, content_dict)
if "conv_id" not in st.session_state:
    st.session_state.conv_id = None

client = GenieClient(HOST, TOKEN, SPACE_ID)

# 渲染历史
for role, payload in st.session_state.history:
    with st.chat_message(role):
        if role == "user":
            st.markdown(payload)
        else:
            if payload.get("text"):
                st.markdown(payload["text"])
            if payload.get("sql"):
                with st.expander("🔍 查看 Genie 生成的 SQL"):
                    st.code(payload["sql"], language="sql")
            df = result_to_df(payload.get("result"))
            if not df.empty:
                st.dataframe(df, use_container_width=True)
                # 自动可视化：1 文本列 + 1 数字列时绘制 bar
                num_cols = df.select_dtypes("number").columns.tolist()
                cat_cols = [c for c in df.columns if c not in num_cols]
                if len(num_cols) >= 1 and len(cat_cols) >= 1 and len(df) <= 50:
                    try:
                        st.bar_chart(df.set_index(cat_cols[0])[num_cols[0]])
                    except Exception:
                        pass

# 输入
question = st.chat_input("用中文向数据提问，比如：哪个试验的 SAE 发生率最高？")
if not question and "pending_q" in st.session_state:
    question = st.session_state.pop("pending_q")

if question:
    st.session_state.history.append(("user", question))
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Genie 正在思考、生成 SQL 并查询数据..."):
            try:
                resp = client.ask(question, st.session_state.conv_id)
                st.session_state.conv_id = resp["conversation_id"]
            except Exception as e:
                st.error(f"调用 Genie 失败：{e}")
                st.stop()
        if resp.get("text"):
            st.markdown(resp["text"])
        if resp.get("sql"):
            with st.expander("🔍 查看 Genie 生成的 SQL"):
                st.code(resp["sql"], language="sql")
        df = result_to_df(resp.get("result"))
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            num_cols = df.select_dtypes("number").columns.tolist()
            cat_cols = [c for c in df.columns if c not in num_cols]
            if len(num_cols) >= 1 and len(cat_cols) >= 1 and len(df) <= 50:
                try:
                    st.bar_chart(df.set_index(cat_cols[0])[num_cols[0]])
                except Exception:
                    pass
    st.session_state.history.append(("assistant", resp))
