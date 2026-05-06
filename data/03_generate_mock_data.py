# Databricks notebook source
# MAGIC %md
# MAGIC # 03 - 生成临床试验 Mock 数据
# MAGIC
# MAGIC 在 Databricks Workspace 中：
# MAGIC 1. 创建一个 Python Notebook，把本文件内容粘贴进去（或直接 Import 此 .py 文件作为 Notebook）。
# MAGIC 2. Attach 到一个 **Serverless** 或普通 Cluster（任意 DBR 13+）。
# MAGIC 3. Run All。脚本会向 `genie_demo.clinical.*` 的 10 张表插入数据。
# MAGIC
# MAGIC 数据规模可调：默认 5 试验、20 站点、800 受试者，约 6 万行事实。

# COMMAND ----------

CATALOG = "genie_demo"
SCHEMA  = "clinical"

N_TRIALS   = 5
N_SITES    = 20
N_INVS     = 60
N_PATIENTS = 800

# COMMAND ----------

import random
from datetime import date, timedelta
from pyspark.sql import Row

random.seed(42)

spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")

# 助手：根据目标表的 schema 把 DataFrame 各列 cast 后插入，保留 DDL 中的 COMMENT
def write_table(rows, table_name: str):
    target = spark.table(table_name)
    df = spark.createDataFrame(rows)
    cast_cols = []
    for f in target.schema.fields:
        if f.name in df.columns:
            cast_cols.append(f"CAST(`{f.name}` AS {f.dataType.simpleString()}) AS `{f.name}`")
    df.selectExpr(*cast_cols).write.insertInto(table_name, overwrite=True)
    print(f"✓ {table_name}: {spark.table(table_name).count()} rows")

# COMMAND ----------
# MAGIC %md ## 维度：trials

# COMMAND ----------

therapeutic_areas = ["Oncology", "Cardiology", "Neurology", "Immunology", "Rare Disease"]
indications = {
    "Oncology":    ["NSCLC", "Breast Cancer", "Colorectal Cancer", "Multiple Myeloma"],
    "Cardiology":  ["Heart Failure", "Atrial Fibrillation", "Hypertension"],
    "Neurology":   ["Alzheimer's Disease", "Parkinson's Disease", "Multiple Sclerosis"],
    "Immunology":  ["Rheumatoid Arthritis", "Psoriasis", "Crohn's Disease"],
    "Rare Disease":["Spinal Muscular Atrophy", "Cystic Fibrosis"],
}
phases = ["Phase I", "Phase II", "Phase III", "Phase IV"]
statuses = ["Recruiting", "Active", "Completed", "Terminated"]
sponsors = ["Contoso Pharma", "Fabrikam BioTech", "Northwind Therapeutics", "Adventure Biopharma"]

trials = []
for i in range(1, N_TRIALS + 1):
    ta = random.choice(therapeutic_areas)
    start = date(2022, 1, 1) + timedelta(days=random.randint(0, 600))
    trials.append(Row(
        trial_id=f"TRL-{i:04d}",
        protocol_code=f"PROT-{ta[:3].upper()}-{i:03d}",
        trial_name=f"{random.choice(['Study','Trial','Investigation'])} of Compound {chr(64+i)} in {random.choice(indications[ta])}",
        therapeutic_area=ta,
        indication=random.choice(indications[ta]),
        phase=random.choice(phases),
        status=random.choice(statuses),
        start_date=start,
        end_date=start + timedelta(days=random.randint(365, 1095)),
        sponsor=random.choice(sponsors),
        target_enrollment=random.choice([100, 200, 300, 500])
    ))
write_table(trials, "trials")

# COMMAND ----------
# MAGIC %md ## 维度：sites

# COMMAND ----------

regions = {
    "APAC":          [("China","Shanghai"),("China","Beijing"),("Japan","Tokyo"),("Australia","Sydney"),("Singapore","Singapore")],
    "EMEA":          [("UK","London"),("Germany","Berlin"),("France","Paris"),("Spain","Madrid")],
    "North America": [("USA","Boston"),("USA","San Francisco"),("USA","New York"),("Canada","Toronto")],
    "LATAM":         [("Brazil","Sao Paulo"),("Mexico","Mexico City")],
}
flat_locs = [(r,c,city) for r, lst in regions.items() for (c,city) in lst]

sites = []
for i in range(1, N_SITES + 1):
    region, country, city = random.choice(flat_locs)
    sites.append(Row(
        site_id=f"SITE-{i:03d}",
        site_name=f"{city} Medical Center {i}",
        country=country,
        region=region,
        city=city,
        activation_date=date(2022,1,1)+timedelta(days=random.randint(0,500))
    ))
write_table(sites, "sites")

# COMMAND ----------
# MAGIC %md ## 维度：investigators

# COMMAND ----------

site_ids = [f"SITE-{i:03d}" for i in range(1, N_SITES+1)]
first_names = ["Wei","Li","Ming","Yan","Sarah","John","Emma","Carlos","Hiroshi","Anna","Liu","Chen","Maria"]
last_names  = ["Wang","Zhang","Smith","Johnson","Garcia","Tanaka","Schmidt","Liu","Chen","Brown"]
roles = ["Principal Investigator","Sub-Investigator","Coordinator"]

invs = []
for i in range(1, N_INVS + 1):
    invs.append(Row(
        investigator_id=f"INV-{i:04d}",
        full_name=f"Dr. {random.choice(first_names)} {random.choice(last_names)}",
        site_id=random.choice(site_ids),
        role=random.choices(roles, weights=[1,2,1])[0]
    ))
write_table(invs, "investigators")

# COMMAND ----------
# MAGIC %md ## 维度：drugs

# COMMAND ----------

drugs = [
    Row(drug_id="DRG-001", drug_name="Compound-A", drug_class="Kinase Inhibitor", is_placebo=False),
    Row(drug_id="DRG-002", drug_name="Compound-B", drug_class="Monoclonal Antibody", is_placebo=False),
    Row(drug_id="DRG-003", drug_name="Compound-C", drug_class="Small Molecule", is_placebo=False),
    Row(drug_id="DRG-004", drug_name="Compound-D", drug_class="ACE Inhibitor", is_placebo=False),
    Row(drug_id="DRG-005", drug_name="Compound-E", drug_class="Anti-TNF Biologic", is_placebo=False),
    Row(drug_id="PLB-001", drug_name="Placebo",    drug_class="Placebo",          is_placebo=True),
]
write_table(drugs, "drugs")

# COMMAND ----------
# MAGIC %md ## 维度：patients

# COMMAND ----------

ethnicities = ["Asian","Caucasian","Hispanic","African","Other"]
comorb_pool = ["Hypertension","Diabetes","Hyperlipidemia","Asthma","CKD","COPD"]

patients = []
for i in range(1, N_PATIENTS + 1):
    age = random.randint(18, 85)
    co  = random.sample(comorb_pool, k=random.randint(0,3))
    patients.append(Row(
        patient_id=f"PT-{i:05d}",
        age=age,
        sex=random.choice(["M","F"]),
        ethnicity=random.choice(ethnicities),
        bmi=round(random.uniform(18.0, 35.0), 1),
        smoker=random.random() < 0.25,
        comorbidities=", ".join(co) if co else None,
        enrollment_date=date(2023,1,1)+timedelta(days=random.randint(0,500))
    ))
write_table(patients, "patients")

# COMMAND ----------
# MAGIC %md ## 事实：enrollments

# COMMAND ----------

trial_rows = spark.table("trials").collect()
trial_ids  = [t.trial_id for t in trial_rows]
inv_rows   = spark.table("investigators").collect()
drug_ids   = [d.drug_id for d in spark.table("drugs").collect() if not d.is_placebo]

withdrawal_reasons = ["Adverse Event","Lack of Efficacy","Patient Decision","Lost to Follow-up","Completed"]
arms = ["Treatment","Control","Placebo"]

enrollments = []
for i in range(1, N_PATIENTS + 1):
    arm = random.choices(arms, weights=[5,3,2])[0]
    drug = "PLB-001" if arm == "Placebo" else random.choice(drug_ids)
    inv = random.choice(inv_rows)
    enrolled = date(2023,1,1)+timedelta(days=random.randint(0,500))
    withdrawn = None
    reason = None
    if random.random() < 0.30:
        withdrawn = enrolled + timedelta(days=random.randint(30, 400))
        reason = random.choice(withdrawal_reasons)
    enrollments.append(Row(
        enrollment_id=f"ENR-{i:05d}",
        patient_id=f"PT-{i:05d}",
        trial_id=random.choice(trial_ids),
        site_id=inv.site_id,
        investigator_id=inv.investigator_id,
        arm=arm,
        drug_id=drug,
        enrollment_date=enrolled,
        withdrawal_date=withdrawn,
        withdrawal_reason=reason
    ))
write_table(enrollments, "enrollments")

# COMMAND ----------
# MAGIC %md ## 事实：visits

# COMMAND ----------

enr_rows = spark.table("enrollments").collect()
visit_types = ["Screening","Baseline","Treatment","Treatment","Treatment","Follow-up","End of Study"]

visits = []
vid = 1
for e in enr_rows:
    n_visits = random.randint(3, 7)
    for k in range(n_visits):
        d = e.enrollment_date + timedelta(days=k*30 + random.randint(-3,3))
        if e.withdrawal_date and d > e.withdrawal_date:
            break
        visits.append(Row(
            visit_id=f"VIS-{vid:07d}",
            enrollment_id=e.enrollment_id,
            visit_number=k+1,
            visit_type=visit_types[min(k, len(visit_types)-1)],
            visit_date=d,
            is_completed=random.random() < 0.95
        ))
        vid += 1
write_table(visits, "visits")

# COMMAND ----------
# MAGIC %md ## 事实：adverse_events

# COMMAND ----------

ae_terms = {
    "Gastrointestinal": ["Nausea","Vomiting","Diarrhea","Abdominal Pain"],
    "Nervous System":   ["Headache","Dizziness","Insomnia"],
    "Blood":            ["Neutropenia","Anemia","Thrombocytopenia"],
    "Skin":             ["Rash","Pruritus"],
    "General":          ["Fatigue","Fever","Pain"],
    "Hepatobiliary":    ["ALT Elevated","AST Elevated"],
}
relateds = ["Unrelated","Possible","Probable","Definite"]
outcomes = ["Recovered","Recovering","Not Recovered","Fatal","Unknown"]

aes = []
aid = 1
for e in enr_rows:
    n_ae = random.choices([0,1,2,3,4,5], weights=[20,30,25,15,7,3])[0]
    # Treatment 组发生 AE 概率略高
    if e.arm != "Treatment" and n_ae > 0:
        n_ae = max(0, n_ae - 1)
    for _ in range(n_ae):
        soc = random.choice(list(ae_terms.keys()))
        grade = random.choices([1,2,3,4,5], weights=[40,30,18,8,4])[0]
        is_serious = grade >= 3
        onset = e.enrollment_date + timedelta(days=random.randint(7, 300))
        resolved = onset + timedelta(days=random.randint(1, 45)) if random.random() < 0.7 else None
        aes.append(Row(
            ae_id=f"AE-{aid:07d}",
            enrollment_id=e.enrollment_id,
            event_term=random.choice(ae_terms[soc]),
            system_organ_class=soc,
            severity=["Mild","Moderate","Severe","Severe","Severe"][grade-1],
            ctcae_grade=grade,
            is_serious=is_serious,
            related_to_drug=random.choice(relateds),
            onset_date=onset,
            resolved_date=resolved,
            outcome=random.choice(outcomes) if grade < 5 else "Fatal"
        ))
        aid += 1
write_table(aes, "adverse_events")

# COMMAND ----------
# MAGIC %md ## 事实：lab_results

# COMMAND ----------

lab_specs = {
    # name: (unit, ref_low, ref_high, mean, sd)
    "ALT":        ("U/L",   7,   45,   30,   20),
    "AST":        ("U/L",   8,   40,   28,   18),
    "Hemoglobin": ("g/dL", 12,   17,   13.5, 1.8),
    "Creatinine": ("mg/dL", 0.6, 1.3,  0.95, 0.3),
    "WBC":        ("10^9/L",4,   11,   7.0,  2.5),
    "Glucose":    ("mg/dL", 70, 110,   95,   25),
}

vis_rows = spark.table("visits").collect()
labs = []
lid = 1
for v in vis_rows:
    if v.visit_type in ("Screening","Baseline","Treatment","End of Study"):
        for test, (unit, lo, hi, mean, sd) in lab_specs.items():
            val = round(random.gauss(mean, sd), 2)
            labs.append(Row(
                lab_id=f"LAB-{lid:08d}",
                enrollment_id=v.enrollment_id,
                visit_id=v.visit_id,
                test_name=test,
                test_value=val,
                unit=unit,
                reference_low=float(lo),
                reference_high=float(hi),
                is_abnormal=(val < lo or val > hi),
                collected_date=v.visit_date
            ))
            lid += 1
write_table(labs, "lab_results")

# COMMAND ----------
# MAGIC %md ## 事实：dosing

# COMMAND ----------

doses = []
did = 1
for e in enr_rows:
    if e.arm == "Placebo":
        amount_pool = [0.0]
    else:
        amount_pool = [25.0, 50.0, 100.0, 200.0]
    end = e.withdrawal_date or (e.enrollment_date + timedelta(days=180))
    days = (end - e.enrollment_date).days
    for k in range(0, days, 7):  # 每周一次
        doses.append(Row(
            dose_id=f"DOS-{did:08d}",
            enrollment_id=e.enrollment_id,
            drug_id=e.drug_id,
            dose_amount_mg=random.choice(amount_pool),
            dose_date=e.enrollment_date + timedelta(days=k),
            is_skipped=random.random() < 0.05
        ))
        did += 1
write_table(doses, "dosing")

# COMMAND ----------
# MAGIC %md ## 验证

# COMMAND ----------

for t in ["trials","sites","investigators","drugs","patients","enrollments","visits","adverse_events","lab_results","dosing"]:
    cnt = spark.table(t).count()
    print(f"{t:20s}: {cnt:>8d} 行")
