-- ============================================================
-- 02_create_tables.sql
-- 临床试验数据模型 DDL（Unity Catalog 管理表，使用 Delta）
-- 维度：trials, sites, patients, investigators, drugs
-- 事实：enrollments, visits, adverse_events, lab_results, dosing
--
-- 注意：所有列与表均带 COMMENT，Genie 会自动读取作为元数据，
--      帮助它准确理解字段含义 —— 这是 Genie 高准确率的关键。
-- ============================================================

USE CATALOG genie_demo;
USE SCHEMA clinical;

-- ---------- 维度：临床试验 ----------
CREATE OR REPLACE TABLE trials (
  trial_id        STRING  NOT NULL COMMENT '临床试验唯一编号，例如 TRL-0001',
  protocol_code   STRING           COMMENT '方案编号 / Protocol Code',
  trial_name      STRING           COMMENT '试验名称',
  therapeutic_area STRING          COMMENT '治疗领域：Oncology / Cardiology / Neurology / Immunology / Rare Disease',
  indication      STRING           COMMENT '适应症（具体疾病），例如 NSCLC, Breast Cancer, Type 2 Diabetes',
  phase           STRING           COMMENT '试验阶段：Phase I / Phase II / Phase III / Phase IV',
  status          STRING           COMMENT '试验状态：Planned / Recruiting / Active / Completed / Terminated',
  start_date      DATE             COMMENT '试验开始日期',
  end_date        DATE             COMMENT '试验结束（计划或实际）日期',
  sponsor         STRING           COMMENT '申办方',
  target_enrollment INT            COMMENT '计划入组受试者数量'
) USING DELTA
COMMENT '临床试验主数据：每行代表一项临床试验';

-- ---------- 维度：研究中心 / 站点 ----------
CREATE OR REPLACE TABLE sites (
  site_id         STRING NOT NULL COMMENT '站点唯一编号',
  site_name       STRING          COMMENT '研究中心名称',
  country         STRING          COMMENT '国家',
  region          STRING          COMMENT '区域：APAC / EMEA / North America / LATAM',
  city            STRING          COMMENT '城市',
  activation_date DATE            COMMENT '站点激活日期'
) USING DELTA
COMMENT '临床研究中心 / 站点';

-- ---------- 维度：研究者 ----------
CREATE OR REPLACE TABLE investigators (
  investigator_id STRING NOT NULL COMMENT '研究者唯一编号',
  full_name       STRING          COMMENT '研究者姓名',
  site_id         STRING          COMMENT '所属站点',
  role            STRING          COMMENT '角色：Principal Investigator / Sub-Investigator / Coordinator'
) USING DELTA
COMMENT '研究者 / PI 信息';

-- ---------- 维度：受试者 / 患者 ----------
CREATE OR REPLACE TABLE patients (
  patient_id      STRING NOT NULL COMMENT '受试者唯一编号 / Subject ID',
  age             INT             COMMENT '入组时年龄',
  sex             STRING          COMMENT '性别：M / F',
  ethnicity       STRING          COMMENT '种族',
  bmi             DOUBLE          COMMENT 'Body Mass Index 体质指数',
  smoker          BOOLEAN         COMMENT '是否吸烟',
  comorbidities   STRING          COMMENT '合并症（逗号分隔），例如 Hypertension, Diabetes',
  enrollment_date DATE            COMMENT '入组日期'
) USING DELTA
COMMENT '受试者去标识化人口学数据';

-- ---------- 维度：研究药物 ----------
CREATE OR REPLACE TABLE drugs (
  drug_id        STRING NOT NULL COMMENT '药物编号',
  drug_name      STRING          COMMENT '药物名称（化合物代号或商品名）',
  drug_class     STRING          COMMENT '药物类别',
  is_placebo     BOOLEAN         COMMENT '是否为安慰剂'
) USING DELTA
COMMENT '研究药物字典';

-- ---------- 事实：入组登记（受试者-试验-站点-治疗组） ----------
CREATE OR REPLACE TABLE enrollments (
  enrollment_id   STRING NOT NULL COMMENT '入组记录编号',
  patient_id      STRING          COMMENT '受试者编号',
  trial_id        STRING          COMMENT '试验编号',
  site_id         STRING          COMMENT '入组站点',
  investigator_id STRING          COMMENT '主要研究者',
  arm             STRING          COMMENT '治疗组：Treatment / Control / Placebo',
  drug_id         STRING          COMMENT '分配的药物',
  enrollment_date DATE            COMMENT '入组日期',
  withdrawal_date DATE            COMMENT '退出日期（NULL 表示在组）',
  withdrawal_reason STRING        COMMENT '退出原因：Adverse Event / Lack of Efficacy / Patient Decision / Lost to Follow-up / Completed'
) USING DELTA
COMMENT '受试者入组事实表';

-- ---------- 事实：访视 ----------
CREATE OR REPLACE TABLE visits (
  visit_id        STRING NOT NULL COMMENT '访视编号',
  enrollment_id   STRING          COMMENT '关联入组',
  visit_number    INT             COMMENT '访视序号 1=Screening, 2=Baseline, ...',
  visit_type      STRING          COMMENT '访视类型：Screening / Baseline / Treatment / Follow-up / End of Study',
  visit_date      DATE            COMMENT '实际访视日期',
  is_completed    BOOLEAN         COMMENT '访视是否完成'
) USING DELTA
COMMENT '受试者访视记录';

-- ---------- 事实：不良事件 (AE / SAE) ----------
CREATE OR REPLACE TABLE adverse_events (
  ae_id           STRING NOT NULL COMMENT '不良事件编号',
  enrollment_id   STRING          COMMENT '关联入组',
  event_term      STRING          COMMENT 'MedDRA 术语 / 事件描述，例如 Headache, Nausea, Neutropenia',
  system_organ_class STRING       COMMENT '系统器官分类 (SOC)',
  severity        STRING          COMMENT '严重程度：Mild / Moderate / Severe',
  ctcae_grade     INT             COMMENT 'CTCAE 等级 1-5',
  is_serious      BOOLEAN         COMMENT '是否为严重不良事件 (SAE)',
  related_to_drug STRING          COMMENT '与研究药物的相关性：Unrelated / Possible / Probable / Definite',
  onset_date      DATE            COMMENT '发生日期',
  resolved_date   DATE            COMMENT '消解日期（NULL 表示未消解）',
  outcome         STRING          COMMENT '转归：Recovered / Recovering / Not Recovered / Fatal / Unknown'
) USING DELTA
COMMENT '不良事件事实表（CTCAE 等级越高越严重；is_serious=TRUE 即 SAE）';

-- ---------- 事实：实验室检查结果 ----------
CREATE OR REPLACE TABLE lab_results (
  lab_id          STRING NOT NULL COMMENT '检验记录编号',
  enrollment_id   STRING          COMMENT '关联入组',
  visit_id        STRING          COMMENT '关联访视',
  test_name       STRING          COMMENT '检验项目：ALT / AST / Hemoglobin / Creatinine / WBC / Glucose',
  test_value      DOUBLE          COMMENT '检验值',
  unit            STRING          COMMENT '单位',
  reference_low   DOUBLE          COMMENT '参考下限',
  reference_high  DOUBLE          COMMENT '参考上限',
  is_abnormal     BOOLEAN         COMMENT '是否超出参考范围',
  collected_date  DATE            COMMENT '采样日期'
) USING DELTA
COMMENT '实验室检验结果';

-- ---------- 事实：给药记录 ----------
CREATE OR REPLACE TABLE dosing (
  dose_id         STRING NOT NULL COMMENT '给药记录编号',
  enrollment_id   STRING          COMMENT '关联入组',
  drug_id         STRING          COMMENT '药物',
  dose_amount_mg  DOUBLE          COMMENT '剂量(mg)',
  dose_date       DATE            COMMENT '给药日期',
  is_skipped      BOOLEAN         COMMENT '是否漏服 / 跳过'
) USING DELTA
COMMENT '给药记录事实表';

-- 验证
SHOW TABLES IN genie_demo.clinical;
