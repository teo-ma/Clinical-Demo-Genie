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

import json
import os
import time
from typing import Optional

import pandas as pd
import plotly.express as px
import requests
import streamlit as st


# -----------------------------------------------------------------
# 自动可视化：根据数据形态选最合适的图表 + 用户手动覆盖
# -----------------------------------------------------------------
_PLOTLY_TEMPLATE = "plotly_white"
_COLOR_SEQ = px.colors.qualitative.Set2

# 列名关键字 → 语义提示
_PCT_KEYWORDS = ("rate", "pct", "percent", "ratio", "占比", "比例", "率")
_GEO_LAT_KEYWORDS = ("lat", "latitude", "纬度")
_GEO_LNG_KEYWORDS = ("lng", "lon", "longitude", "经度")
# 只看列名，不再解析值，避免整数 ID 被误判为时间戳
_TIME_KEYWORDS = ("date", "month", "year", "week", "quarter", "日期", "月份", "年份", "季度")
# ID 类名字不该当作连续量（即使是数字）
_ID_KEYWORDS = ("id", "_id", "编号", "代码")

CHART_OPTIONS = ["自动", "KPI", "柱状图", "横向柱状图", "饼图", "环形图",
                 "折线图", "面积图", "散点图", "地图", "表格"]


def _is_time_col(col_name: str, series: pd.Series) -> bool:
    """仅凭列名判断；如果是数值型列且列名不含时间关键字，返回 False。避免把 site_id/patient_id 误判为时间。"""
    name = col_name.lower()
    if any(k in name for k in _TIME_KEYWORDS):
        return True
    # 只有字符串/日期型才尝试解析；数字一律不当时间
    if pd.api.types.is_numeric_dtype(series):
        return False
    if any(k in name for k in _ID_KEYWORDS):
        return False
    try:
        sample = series.dropna().astype(str).head(5)
        if sample.empty:
            return False
        # 必须同时含日期分隔符（避免纯数字被解析为纳秒时间戳）
        if not sample.str.contains(r"[-/:]").any():
            return False
        pd.to_datetime(sample, errors="raise")
        return True
    except Exception:
        return False


def _is_pct_col(col_name: str) -> bool:
    return any(k in col_name.lower() for k in _PCT_KEYWORDS)


def _bar_text_format(series: pd.Series) -> str:
    """根据数值列选合适的柱状图数字标签格式。
    - 列名包含百分比关键字 → .1%
    - 全部为整数 → ,d（带千位分隔，不丢精度）
    - 其他 → .3~f（3 位有效数字，不会把 401 舍入为 400）
    """
    name = series.name or ""
    if _is_pct_col(str(name)):
        return ".1%"
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return ""
    if (s % 1 == 0).all():
        return ",d"
    return ".3~f"


def _classify(df: pd.DataFrame):
    """返回 (num_cols, cat_cols, time_cols, lat_col, lng_col)"""
    num_cols = df.select_dtypes("number").columns.tolist()
    cat_cols = [c for c in df.columns if c not in num_cols]
    time_cols = [c for c in df.columns if _is_time_col(c, df[c])]
    lat_col = next((c for c in df.columns
                    if any(k in c.lower() for k in _GEO_LAT_KEYWORDS)), None)
    lng_col = next((c for c in df.columns
                    if any(k in c.lower() for k in _GEO_LNG_KEYWORDS)), None)
    return num_cols, cat_cols, time_cols, lat_col, lng_col


def suggest_chart_type(df: pd.DataFrame) -> str:
    """硬规则推荐默认图表类型，返回 CHART_OPTIONS 中的某一项。"""
    if df is None or df.empty:
        return "表格"
    num_cols, cat_cols, time_cols, lat_col, lng_col = _classify(df)
    n_rows = len(df)

    # 1. 单值 KPI
    if n_rows == 1 and len(num_cols) == 1 and len(df.columns) == 1:
        return "KPI"
    # 2. 地理坐标 → 地图
    if lat_col and lng_col:
        return "地图"
    # 3. 时间序列 → 折线/面积
    if time_cols and num_cols:
        return "面积图" if len(num_cols) == 1 and not [c for c in cat_cols if c not in time_cols] else "折线图"
    # 4. 行数过多 → 表格
    if n_rows > 200:
        return "表格"
    # 5. 一文本一数字
    if num_cols and cat_cols:
        # 占比类 + 行数少 → 饼图
        if n_rows <= 8 and len(num_cols) == 1 and (df[num_cols[0]] >= 0).all():
            if _is_pct_col(num_cols[0]) or n_rows <= 6:
                return "饼图"
            return "环形图"
        # 类目名很长 → 横向柱状图
        if df[cat_cols[0]].astype(str).str.len().max() > 12 or n_rows > 12:
            return "横向柱状图"
        return "柱状图"
    # 6. 两个数字 → 散点
    if len(num_cols) >= 2:
        return "散点图"
    return "表格"


def render_chart(df: pd.DataFrame, chart_type: str):
    """根据 chart_type 渲染对应 Plotly figure；不适合则返回 None。"""
    if df is None or df.empty:
        return None
    num_cols, cat_cols, time_cols, lat_col, lng_col = _classify(df)
    common = dict(template=_PLOTLY_TEMPLATE, color_discrete_sequence=_COLOR_SEQ)

    try:
        if chart_type == "KPI":
            return None  # 由调用方用 st.metric 渲染
        if chart_type == "表格":
            return None

        if chart_type in ("饼图", "环形图") and num_cols and cat_cols:
            d = df.sort_values(num_cols[0], ascending=False).head(10)
            fig = px.pie(d, names=cat_cols[0], values=num_cols[0],
                         hole=0.35 if chart_type == "环形图" else 0,
                         **common)
            fig.update_traces(textposition="inside", textinfo="percent+label")

        elif chart_type == "横向柱状图" and num_cols and cat_cols:
            d = df.sort_values(num_cols[0], ascending=True).tail(50)
            fmt = _bar_text_format(d[num_cols[0]])
            fig = px.bar(d, x=num_cols[0], y=cat_cols[0],
                         orientation="h", text_auto=fmt, **common)
            fig.update_traces(textposition="outside", cliponaxis=False)

        elif chart_type == "柱状图" and num_cols and cat_cols:
            d = df.sort_values(num_cols[0], ascending=False).head(50)
            fmt = _bar_text_format(d[num_cols[0]])
            fig = px.bar(d, x=cat_cols[0], y=num_cols[0],
                         text_auto=fmt, **common)
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_xaxes(tickangle=-30)

        elif chart_type in ("折线图", "面积图") and num_cols:
            x = (time_cols or cat_cols or [df.columns[0]])[0]
            y = num_cols[0]
            d = df.copy()
            if x in time_cols:
                d[x] = pd.to_datetime(d[x])
            d = d.sort_values(x)
            color = next((c for c in cat_cols if c != x), None)
            if chart_type == "面积图":
                fig = px.area(d, x=x, y=y, color=color, **common)
            else:
                fig = px.line(d, x=x, y=y, color=color, markers=True, **common)

        elif chart_type == "散点图" and len(num_cols) >= 2:
            color = cat_cols[0] if cat_cols else None
            fig = px.scatter(df, x=num_cols[0], y=num_cols[1],
                             color=color, **common)

        elif chart_type == "地图" and lat_col and lng_col:
            size = num_cols[0] if num_cols else None
            fig = px.scatter_mapbox(df, lat=lat_col, lon=lng_col, size=size,
                                    zoom=2, mapbox_style="open-street-map",
                                    **common)
        else:
            return None
    except Exception:
        return None

    # 百分比列格式化
    for c in num_cols:
        if _is_pct_col(c):
            fig.update_yaxes(tickformat=".1%")
            break

    fig.update_layout(
        margin=dict(l=10, r=10, t=30, b=10),
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1),
        font=dict(size=13),
    )
    return fig


def render_kpi(df: pd.DataFrame):
    """单值 KPI 卡片渲染"""
    val = df.iloc[0, 0]
    label = df.columns[0]
    try:
        if isinstance(val, (int, float)) and abs(val) >= 1000:
            display = f"{val:,.0f}"
        elif isinstance(val, float):
            display = f"{val:,.2f}"
        else:
            display = str(val)
    except Exception:
        display = str(val)
    st.metric(label=label, value=display)


def render_visualization(df: pd.DataFrame, key: str):
    """完整渲染：表格 + 默认图表 + 用户切换 selectbox。"""
    if df is None or df.empty:
        return
    default = suggest_chart_type(df)
    default_idx = CHART_OPTIONS.index(default) if default in CHART_OPTIONS else 0

    col_t, col_c = st.columns([1, 3])
    with col_t:
        chart_type = st.selectbox(
            "图表类型",
            CHART_OPTIONS,
            index=default_idx,
            key=f"chart_type_{key}",
            help=f"系统建议：{default}",
        )
    with col_c:
        st.caption(f"💡 系统根据数据自动推荐：**{default}**")

    if chart_type in ("自动",):
        chart_type = default

    # 表格 + KPI 单独处理
    if chart_type == "KPI" and len(df) == 1:
        render_kpi(df)
        with st.expander("查看原始数据"):
            st.dataframe(df, use_container_width=True, hide_index=True,
                         key=f"df_kpi_{key}")
        return
    if chart_type == "表格":
        st.dataframe(df, use_container_width=True, hide_index=True,
                     key=f"df_table_{key}")
        return

    # 其他图表：先表格再图
    st.dataframe(df, use_container_width=True, hide_index=True,
                 key=f"df_{key}")
    fig = render_chart(df, chart_type)
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True,
                        key=f"plot_{key}_{chart_type}")
    else:
        st.caption(f"⚠️ 当前数据不适合渲染为「{chart_type}」")


# -----------------------------------------------------------------
# OAuth M2M helper: resolve a short-lived bearer token for a SP
# -----------------------------------------------------------------
_OAUTH_CACHE: dict = {}


def _oauth_token(host: str, client_id: str, client_secret: str) -> str:
    cache_key = (host, client_id)
    cached = _OAUTH_CACHE.get(cache_key)
    if cached and cached["exp"] > time.time() + 60:
        return cached["token"]
    r = requests.post(
        f"{host.rstrip('/')}/oidc/v1/token",
        auth=(client_id, client_secret),
        data={"grant_type": "client_credentials", "scope": "all-apis"},
        timeout=30,
    )
    r.raise_for_status()
    body = r.json()
    token = body["access_token"]
    expires_in = int(body.get("expires_in", 3600))
    _OAUTH_CACHE[cache_key] = {"token": token, "exp": time.time() + expires_in}
    return token


def _resolve_token(host: str, persona: dict) -> str:
    """Return a bearer token for the persona; supports either static `token`
    or OAuth M2M via `client_id` + `client_secret`."""
    if persona.get("token"):
        return persona["token"]
    cid = persona.get("client_id")
    csec = persona.get("client_secret")
    if cid and csec:
        return _oauth_token(host, cid, csec)
    return ""


# -----------------------------------------------------------------
# 演示用户（Persona）配置
# -----------------------------------------------------------------
# 每个 persona 对应一个 Databricks 账号的 PAT 和一个 Genie Space，
# 以此演示“不同权限的用户看到不同数据”。
#
# 优先从环境变量 GENIE_PERSONAS（JSON）加载，示例：
#   GENIE_PERSONAS='[
#     {"label":"🏥 Site Manager (China)","space_id":"...","token":"dapi...","scope":"仅中国站点数据"},
#     {"label":"🔎 Safety Reviewer","space_id":"...","token":"dapi...","scope":"全部 AE / 明文 PII"},
#     {"label":"📊 Executive","space_id":"...","token":"dapi...","scope":"仅 KPI 汇总"}
#   ]'
# 未设置时 fallback 到单一 DATABRICKS_TOKEN + GENIE_SPACE_ID（老逻辑）。
def _load_personas() -> list:
    raw = os.getenv("GENIE_PERSONAS", "").strip()
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, list) and data:
                return data
        except Exception:
            pass
    # fallback: 单用户模式
    return [{
        "label": "Default User",
        "space_id": os.getenv("GENIE_SPACE_ID", ""),
        "token": os.getenv("DATABRICKS_TOKEN", ""),
        "scope": "当前 Token 对应账号的完整 UC 权限",
    }]


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
    # 尝试把数字列转 numeric（pandas 2.2+ 已移除 errors='ignore'，需手动处理）
    for c in df.columns:
        converted = pd.to_numeric(df[c], errors="coerce")
        # 只在转换后没有新增 NaN 时才接受（避免占用原本是文本的列）
        if converted.notna().sum() == df[c].notna().sum():
            df[c] = converted
    return df


# -----------------------------------------------------------------
# UI
# -----------------------------------------------------------------
st.set_page_config(page_title="Clinical Genie · 临床数据问答", page_icon="🧬", layout="wide")

# 全局样式：徽章
st.markdown(
    """
    <style>
    .badge {display:inline-block;padding:1px 7px;border-radius:9px;
        font-size:10.5px;font-weight:600;margin:0 4px 4px 0;line-height:1.5;}
    .badge-row  {background:#FFF1E6;color:#B5530E;border:1px solid #F4C49A;}
    .badge-mask {background:#E7F1FF;color:#0B5BD3;border:1px solid #B7D2F7;}
    .badge-mv   {background:#EAF7EC;color:#1B7A33;border:1px solid #B5E0BC;}
    .badge-base {background:#F1F1F1;color:#444;border:1px solid #D5D5D5;}
    .feature-card {border:1px solid #E4E4E4;border-radius:8px;
        padding:10px 14px;margin-bottom:8px;background:#FAFAFA;}
    .feature-card h5 {margin:0 0 4px 0;font-size:13px;}
    .feature-card p  {margin:0;font-size:12px;color:#555;}
    /* sidebar 紧凑：按钮文本左对齐 + 减小间距 */
    section[data-testid="stSidebar"] button {
        text-align:left !important;
        white-space:normal !important;
        line-height:1.35 !important;
        padding:6px 10px !important;
        font-size:13px !important;
    }
    section[data-testid="stSidebar"] .stButton {margin-bottom:2px;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🧬 Clinical Genie · 临床试验自然语言问答")
st.caption("基于 Azure Databricks AI/BI Genie · Unity Catalog 全栈数据治理演示")

HOST = os.getenv("DATABRICKS_HOST", "")
PERSONAS = _load_personas()

# ---------------- 顶部：特性总览（折叠） ----------------
with st.expander("📌 本 Demo 重点演示的 Genie / Unity Catalog 高级特性", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            "<div class='feature-card'>"
            "<h5><span class='badge badge-row'>行级权限</span> Row Filter</h5>"
            "<p>Site Manager (CN) 仅能查询 <code>country='China'</code> 的研究站点；"
            "Safety Reviewer 可见全球。同一条 SQL，不同身份看到不同行。</p>"
            "</div>",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            "<div class='feature-card'>"
            "<h5><span class='badge badge-mask'>列级脱敏</span> Column Mask</h5>"
            "<p><code>patients</code> 表的 <code>BMI / 是否吸烟 / 合并症</code> 三列：仅 Safety Reviewer 看明文，"
            "Site Manager 看到脱敏值（REDACTED / NULL）。</p>"
            "</div>",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            "<div class='feature-card'>"
            "<h5><span class='badge badge-mv'>指标视图</span> UC Metric Views</h5>"
            "<p>SAE 发生率、入组率、退出率等核心业务指标在 UC 中以 <code>MEASURE()</code> 锁定公式，"
            "由数据团队预审核，Genie 直接调用，避免 LLM 现场计算导致口径不一致。</p>"
            "</div>",
            unsafe_allow_html=True,
        )

# ---------------- 顶部：身份切换 ----------------
col_p, col_s = st.columns([2, 3])
with col_p:
    persona_labels = [p["label"] for p in PERSONAS]
    selected_label = st.selectbox(
        "👤 当前演示用户身份",
        persona_labels,
        index=0,
        help="切换不同身份会使用不同的 Service Principal Token，从而触发 Unity Catalog 行级 / 列级策略",
    )
selected_persona = next(p for p in PERSONAS if p["label"] == selected_label)
with col_s:
    st.info(f"🔐 可访问数据范围：**{selected_persona.get('scope', 'N/A')}**")

# 身份变化时重置会话
if st.session_state.get("_active_persona") != selected_label:
    st.session_state["_active_persona"] = selected_label
    st.session_state.pop("conv_id", None)
    st.session_state.pop("history", None)

SPACE_ID = selected_persona.get("space_id", "")
try:
    TOKEN = _resolve_token(HOST, selected_persona) if HOST else ""
except Exception as e:
    st.error(f"获取身份 Token 失败：{e}")
    st.stop()

with st.sidebar:
    st.subheader("⚙️ 连接配置")
    HOST = st.text_input("Databricks Host", HOST, placeholder="https://adb-xxx.azuredatabricks.net")
    st.text_input("Genie Space ID", SPACE_ID, disabled=True, help="由当前演示身份决定")
    if st.button("🔄 新建会话", use_container_width=True):
        st.session_state.pop("conv_id", None)
        st.session_state.pop("history", None)
        st.rerun()

    st.markdown("---")
    st.subheader("💡 推荐演示问题")
    st.caption("点击问题直接发送到 Genie。徽章标识该问题展示的特性。")

    # 问题分类：每条 = (问题, 徽章列表, 特性说明)
    QUESTION_GROUPS = [
        (
            "🔐 行级权限 / 列级脱敏",
            "切换身份后再次提问，对比返回结果差异",
            [
                ("列出所有研究站点和它们所在国家",
                 ["row"],
                 "Site Manager (CN) 仅看到中国站点；Safety Reviewer 看到全球站点"),
                ("显示前 5 名受试者的合并症、BMI、是否吸烟",
                 ["mask"],
                 "Site Manager 看到脱敏值；Safety Reviewer 看到明文"),
                ("按区域统计入组人数和在组人数",
                 ["row", "mv"],
                 "Metric View + 行级权限：CN 身份只看到 APAC 区域"),
            ],
        ),
        (
            "📊 指标视图（Metric Views）",
            "Genie 直接调用 MEASURE() 函数，公式由 UC 锁定",
            [
                ("按治疗组对比 SAE 发生率",
                 ["mv"],
                 "命中 mv_safety；sae_rate 公式由数据团队预审核"),
                ("各试验的受试者退出率排名",
                 ["mv"],
                 "命中 mv_dropout；dropout_rate 公式锁定"),
                ("各区域每月的入组人数趋势",
                 ["mv"],
                 "命中 mv_enrollment；按 region + enrollment_month 切片"),
            ],
        ),
        (
            "💬 自然语言基础能力",
            "Text-to-SQL、跨表 JOIN、多轮追问",
            [
                ("当前在组的受试者总数？按试验分组列出。", [], None),
                ("最常见的 10 种不良事件是什么？", [], None),
                ("肝功能异常受试者数量按试验分组排序", [], "跨 lab_results / enrollments / trials 三表 JOIN"),
                ("受试者退出原因分布", [], None),
                ("Top 10 入组数最多的研究中心", [], None),
            ],
        ),
    ]

    BADGE_HTML = {
        "row":  "<span class='badge badge-row'>行级权限</span>",
        "mask": "<span class='badge badge-mask'>列脱敏</span>",
        "mv":   "<span class='badge badge-mv'>Metric View</span>",
    }

    for gi, (group_title, group_caption, items) in enumerate(QUESTION_GROUPS):
        with st.expander(group_title, expanded=(gi == 0)):
            st.caption(group_caption)
            for q, badges, hint in items:
                if badges:
                    st.markdown(
                        " ".join(BADGE_HTML[b] for b in badges),
                        unsafe_allow_html=True,
                    )
                if st.button(q, key=f"sg_{q}", use_container_width=True):
                    st.session_state["pending_q"] = q
                if hint:
                    st.markdown(
                        f"<div style='font-size:11px;color:#777;margin:-4px 0 10px 4px;'>↳ {hint}</div>",
                        unsafe_allow_html=True,
                    )

if not (HOST and TOKEN and SPACE_ID):
    st.warning(
        "缺少配置：请确认环境变量 `DATABRICKS_HOST` 已设置，且 `GENIE_PERSONAS` "
        "中至少有一个 persona 提供了 `space_id` 和 `token`。"
    )
    st.stop()

if "history" not in st.session_state:
    st.session_state.history = []  # list of (role, content_dict)
if "conv_id" not in st.session_state:
    st.session_state.conv_id = None

client = GenieClient(HOST, TOKEN, SPACE_ID)

# 渲染历史
for _idx, (role, payload) in enumerate(st.session_state.history):
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
            render_visualization(df, key=f"hist_{_idx}")

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
        render_visualization(df, key=f"new_{resp.get('message_id','x')}")
    st.session_state.history.append(("assistant", resp))
