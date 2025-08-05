import streamlit as st
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
import tempfile
import io
import os
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from fpdf import FPDF
from PIL import Image
from datetime import date

# === Constants ===
LABOR_COST_WORKER = 13.41
LABOR_COST_OFFICE = 31.25
MACHINE_COST = {
    'CNC': 18.33,
    'Robot': 19.79,
    'Autoclave': 49.98
}

# === Logo & Title ===
logo = Image.open("triac_logo.png")
st.image(logo, width=150)
st.set_page_config(page_title="Cost Estimation Tool", layout="wide")
st.title("Triac Project Budget Monitor")

# === Project Info ===
st.markdown("### 📁 Project Information")
project_name = st.text_input("Project Name")
start_date = st.date_input("Start Date", value=date.today())
end_date = st.date_input("End Date", value=date.today())

def parse_number_input(label, default=0.0):
    raw = st.text_input(label, value=f"{default:,.2f}")
    try:
        return round(float(raw.replace(",", "")), 2)
    except:
        return 0.0

# === Inputs ===
st.markdown("### 1. Input Estimate and Actual Data")

with st.expander("🔧 Estimated Cost Input"):
    est_labor_worker = parse_number_input("Estimated Labor Hours - Worker")
    est_labor_office = parse_number_input("Estimated Labor Hours - Office")
    est_machine = {m: parse_number_input(f"Estimated Machine Hours - {m}") for m in MACHINE_COST}
    est_material = parse_number_input("Estimated Material Cost (USD)")

with st.expander("📌 Actual Cost Input"):
    act_labor_worker = st.number_input("Actual Labor Hours - Worker", min_value=0.0, step=0.1)
    act_labor_office = st.number_input("Actual Labor Hours - Office", min_value=0.0, step=0.1)
    act_machine = {m: st.number_input(f"Actual Machine Hours - {m}", min_value=0.0, step=0.1) for m in MACHINE_COST}
    act_material = st.number_input("Actual Material Cost (USD)", min_value=0.0, step=1.0)

with st.expander("🛠️ Additional Actual Cost: Warranty & Afterwork"):
    warranty_cost = st.number_input("Warranty Cost (USD)", min_value=0.0, step=1.0)
    afterwork_cost = st.number_input("Afterwork Cost (USD)", min_value=0.0, step=1.0)

# === Calculations ===
est_cost = {
    "Labor - Worker": est_labor_worker * LABOR_COST_WORKER,
    "Labor - Office": est_labor_office * LABOR_COST_OFFICE,
    "Material": est_material
}
est_cost.update({m: est_machine[m] * MACHINE_COST[m] for m in MACHINE_COST})
est_total = sum(est_cost.values())

act_cost = {
    "Labor - Worker": act_labor_worker * LABOR_COST_WORKER,
    "Labor - Office": act_labor_office * LABOR_COST_OFFICE,
    "Material": act_material
}
act_cost.update({m: act_machine[m] * MACHINE_COST[m] for m in MACHINE_COST})
act_total = sum(act_cost.values())
act_total_with_extra = act_total + warranty_cost + afterwork_cost

# === Manual fallback if no input ===
if est_total == 0 and act_total_with_extra == 0:
    st.warning("⚠️ Không có dữ liệu estimate và actual. Vui lòng nhập giá bán và giá thực tế.")
    est_total = parse_number_input("🟢 Giá đã bán (USD)")
    act_total = parse_number_input("🔴 Giá thực tế đã tính (USD)")
    act_total_with_extra = act_total
    est_cost = {}
    act_cost = {}

# === Summary Table ===
st.markdown("### 2. Summary Table")
summary_df = pd.DataFrame([
    {
        "Category": k,
        "Estimated (USD)": est_cost.get(k, 0),
        "Actual (USD)": act_cost.get(k, 0),
        "Difference (USD)": est_cost.get(k, 0) - act_cost.get(k, 0),
        "Difference (%)": round(((est_cost.get(k, 0) - act_cost.get(k, 0)) / est_cost.get(k, 0)) * 100, 2) if est_cost.get(k, 0) else 0
    } for k in set(est_cost) | set(act_cost)
])
fig_diff = px.bar(summary_df, x="Category", y="Difference (USD)", color="Difference (USD)", title="Cost Difference by Category (USD)")
st.plotly_chart(fig_diff, use_container_width=True)

summary_df[["Estimated (USD)", "Actual (USD)", "Difference (USD)"]] = summary_df[["Estimated (USD)", "Actual (USD)", "Difference (USD)"]].applymap(lambda x: f"${x:,.2f}")
summary_df["Difference (%)"] = summary_df["Difference (%)"].apply(lambda x: f"{x:.2f}%")
st.dataframe(summary_df, use_container_width=True)

# === Pie + Bar Charts ===
if est_cost and act_cost:
    col1, col2 = st.columns(2)
    col1.plotly_chart(px.pie(values=list(est_cost.values()), names=list(est_cost.keys()), title="Estimated Cost Composition"), use_container_width=True)
    col2.plotly_chart(px.pie(values=list(act_cost.values()), names=list(act_cost.keys()), title="Actual Cost Composition"), use_container_width=True)
    st.plotly_chart(px.bar(pd.DataFrame({
        "Category": list(est_cost.keys()),
        "Estimated": list(est_cost.values()),
        "Actual": [act_cost.get(k, 0) for k in est_cost]
    }), x="Category", y=["Estimated", "Actual"], barmode="group", title="Cost Comparison"), use_container_width=True)

# === Final Comparison ===
st.markdown("### 3. Final Comparison")
final_df = pd.DataFrame({
    "Item": [
        "Estimated Total", "Actual Total (No Warranty/Afterwork)",
        "Warranty Cost", "Afterwork Cost", "Actual Total (All Included)",
        "Gap (USD)", "Gap (%)"
    ],
    "Value (USD)": [
        est_total, act_total, warranty_cost, afterwork_cost,
        act_total_with_extra, act_total_with_extra - est_total,
        round((act_total_with_extra - est_total) / est_total * 100, 2) if est_total != 0 else 0.0
    ]
})
# Chart
fig_final = px.bar(final_df[~final_df["Item"].str.contains("Gap (%)")], x="Item", y="Value (USD)", text="Value (USD)", title="Final Cost Comparison (USD)", color="Value (USD)", color_continuous_scale="Blues")
fig_final.update_traces(texttemplate="%{text:$,.2f}", textposition="outside")
st.plotly_chart(fig_final, use_container_width=True)

final_df["Value (USD)"] = final_df.apply(
    lambda row: f"{row['Value (USD)']:.2f}%" if "Gap (%)" in row["Item"] else f"${row['Value (USD)']:,.2f}", axis=1)
st.dataframe(final_df, use_container_width=True)

# === Export Excel + PDF omitted for brevity (giống phần bạn có sẵn) ===
