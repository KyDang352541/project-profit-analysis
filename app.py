import streamlit as st
import pandas as pd
import plotly.express as px
import io
import os
import tempfile
import matplotlib.pyplot as plt
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from fpdf import FPDF
from PIL import Image

# === Constants ===
LABOR_COST_WORKER = 13.41
LABOR_COST_OFFICE = 31.25
MACHINE_COST = {
    'CNC': 18.33,
    'Robot': 19.79,
    'Autoclave': 49.98
}

# === Logo & Title ===
if os.path.exists("triac_logo.png"):
    logo = Image.open("triac_logo.png")
    st.image(logo, width=150)
else:
    st.markdown("### Triac Composites")

st.set_page_config(page_title="Cost Estimation Tool", layout="wide")
st.title("Triac Project Budget Monitor")

# === Project Info ===
st.markdown("### 📁 Project Information")
project_name = st.text_input("Project Name")
start_date = st.date_input("Start Date")
end_date = st.date_input("End Date")

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
    est_machine = {}
    for machine in MACHINE_COST:
        est_machine[machine] = parse_number_input(f"Estimated Machine Hours - {machine}")
    est_material = parse_number_input("Estimated Material Cost (USD)")

with st.expander("📌 Actual Cost Input"):
    act_labor_worker = round(st.number_input("Actual Labor Hours - Worker", min_value=0.0, step=0.1, format="%.2f"), 2)
    act_labor_office = round(st.number_input("Actual Labor Hours - Office", min_value=0.0, step=0.1, format="%.2f"), 2)
    act_machine = {}
    for machine in MACHINE_COST:
        act_machine[machine] = round(st.number_input(f"Actual Machine Hours - {machine}", min_value=0.0, step=0.1, format="%.2f"), 2)
    act_material = round(st.number_input("Actual Material Cost (USD)", min_value=0.0, step=1.0, format="%.2f"), 2)

with st.expander("🛠️ Additional Actual Cost: Warranty & Afterwork"):
    warranty_cost = round(st.number_input("Warranty Cost (USD)", min_value=0.0, step=1.0, format="%.2f"), 2)
    afterwork_cost = round(st.number_input("Afterwork Cost (USD)", min_value=0.0, step=1.0, format="%.2f"), 2)

# === Calculations ===
est_cost = {
    "Labor - Worker": est_labor_worker * LABOR_COST_WORKER,
    "Labor - Office": est_labor_office * LABOR_COST_OFFICE,
    "Material": est_material
}
for machine in MACHINE_COST:
    est_cost[machine] = est_machine[machine] * MACHINE_COST[machine]
est_total = sum(est_cost.values())

act_cost = {
    "Labor - Worker": act_labor_worker * LABOR_COST_WORKER,
    "Labor - Office": act_labor_office * LABOR_COST_OFFICE,
    "Material": act_material
}
for machine in MACHINE_COST:
    act_cost[machine] = act_machine[machine] * MACHINE_COST[machine]
act_total = sum(act_cost.values())
act_total_with_extra = act_total + warranty_cost + afterwork_cost

# === Handling missing estimate or actual total
if est_total == 0 or act_total_with_extra == 0:
    st.warning("⚠️ Một trong hai phần Estimated hoặc Actual không có dữ liệu. Vui lòng nhập thủ công để so sánh.")
    if est_total == 0:
        est_total = parse_number_input("🟢 Nhập thủ công tổng giá bán ước tính (Estimated Total)")
        est_cost = {}
    if act_total_with_extra == 0:
        act_total_with_extra = parse_number_input("🔴 Nhập thủ công tổng chi phí thực tế (Actual Total)")
        act_total = act_total_with_extra - warranty_cost - afterwork_cost
        act_cost = {}

# === Summary Table
st.markdown("### 2. Summary Table")
summary_df = pd.DataFrame()
if est_cost and act_cost:
    summary_df = pd.DataFrame([
        {
            "Category": k,
            "Estimated (USD)": est_cost.get(k, 0),
            "Actual (USD)": act_cost.get(k, 0),
            "Difference (USD)": est_cost.get(k, 0) - act_cost.get(k, 0),
            "Difference (%)": round(((est_cost.get(k, 0) - act_cost.get(k, 0)) / est_cost.get(k, 0)) * 100, 2)
            if est_cost.get(k, 0) else 0
        } for k in set(est_cost) | set(act_cost)
    ])

    fig_diff = px.bar(summary_df, x="Category", y="Difference (USD)", color="Difference (USD)", title="Cost Difference by Category")
    fig_diff.update_layout(height=400)
    st.plotly_chart(fig_diff, use_container_width=True)

    summary_df[["Estimated (USD)", "Actual (USD)", "Difference (USD)"]] = summary_df[["Estimated (USD)", "Actual (USD)", "Difference (USD)"]].applymap(lambda x: f"${x:,.2f}")
    summary_df["Difference (%)"] = summary_df["Difference (%)"].apply(lambda x: f"{x:.2f}%")
    st.dataframe(summary_df, use_container_width=True)
else:
    st.info("Không có dữ liệu chi tiết để hiển thị bảng so sánh từng hạng mục.")

# === Final Summary ===
st.markdown("### 3. Final Comparison")
final_df = pd.DataFrame({
    "Item": [
        "Estimated Total",
        "Actual Total (No Warranty/Afterwork)",
        "Warranty Cost",
        "Afterwork Cost",
        "Actual Total (All Included)",
        "Gap (USD)",
        "Gap (%)"
    ],
    "Value (USD)": [
        est_total,
        act_total,
        warranty_cost,
        afterwork_cost,
        act_total_with_extra,
        act_total_with_extra - est_total,
        round((act_total_with_extra - est_total) / est_total * 100, 2) if est_total != 0 else 0.0
    ]
})

final_df_display = final_df.copy()
final_df_display["Value (USD)"] = final_df_display.apply(
    lambda row: f"{row['Value (USD)']:.2f}%" if "Gap (%)" in row["Item"] else f"${row['Value (USD)']:,.2f}", axis=1
)
st.dataframe(final_df_display, use_container_width=True)
