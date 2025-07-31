import streamlit as st
import pandas as pd
import plotly.express as px
import io
import os
import tempfile               # ✅ THÊM DÒNG NÀY
import matplotlib.pyplot as plt
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from fpdf import FPDF
from PIL import Image
import os
import tempfile
import plotly.io as pio


# === Constants ===
LABOR_COST_WORKER = 13.41
LABOR_COST_OFFICE = 31.25
MACHINE_COST = {
    'CNC': 18.33,
    'Robot': 19.79,
    'Autoclave': 49.98
}
# Hiển thị logo trong giao diện
logo = Image.open("triac_logo.png")
st.image(logo, width=150)  # bạn có thể chỉnh width nếu cần

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
        # Loại dấu phẩy, rồi chuyển sang float
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

# === Summary Table ===
st.markdown("### 2. Summary Table")
data = []
for category in est_cost:
    estimated = est_cost[category]
    actual = act_cost.get(category, 0.0)
    diff = estimated - actual 
    percent_diff = (diff / estimated * 100) if estimated != 0 else 0
    data.append({
        "Category": category,
        "Estimated (USD)": estimated,
        "Actual (USD)": actual,
        "Difference (USD)": diff,
        "Difference (%)": round(percent_diff, 2)
    })
summary_df = pd.DataFrame(data)

# 📊 Biểu đồ Cột: Difference (USD)
fig_diff = px.bar(
    summary_df,
    x="Category", y="Difference (USD)",
    title="Cost Difference by Category (USD)",
    color="Difference (USD)",
    color_continuous_scale='RdYlGn'
)
fig_diff.update_traces(
    text=summary_df["Difference (USD)"].apply(lambda x: f"${x:,.2f}"),
    textposition="outside"
)
fig_diff.update_layout(
    yaxis_title="USD",
    xaxis_title="Category",
    uniformtext_minsize=8,
    uniformtext_mode='hide',
    margin=dict(t=60, b=40),
    height=400
)
st.plotly_chart(fig_diff, use_container_width=True)

# 🔢 Format bảng sau khi biểu đồ đã dùng số thật
summary_df["Estimated (USD)"] = summary_df["Estimated (USD)"].apply(lambda x: f"${x:,.2f}")
summary_df["Actual (USD)"] = summary_df["Actual (USD)"].apply(lambda x: f"${x:,.2f}")
summary_df["Difference (USD)"] = summary_df["Difference (USD)"].apply(lambda x: f"${x:,.2f}")
summary_df["Difference (%)"] = summary_df["Difference (%)"].apply(lambda x: f"{x:.2f}%")

st.dataframe(summary_df, use_container_width=True)

# === Pie Charts ===
col1, col2 = st.columns(2)
with col1:
    fig1 = px.pie(values=list(est_cost.values()), names=list(est_cost.keys()), title="Estimated Cost Composition")
    st.plotly_chart(fig1, use_container_width=True)
with col2:
    fig2 = px.pie(values=list(act_cost.values()), names=list(act_cost.keys()), title="Actual Cost Composition")
    st.plotly_chart(fig2, use_container_width=True)

# === Bar Chart ===
chart_df = pd.DataFrame({
    "Category": list(est_cost.keys()),
    "Estimated": list(est_cost.values()),
    "Actual": [act_cost[k] for k in est_cost.keys()]
})
fig3 = px.bar(chart_df, x="Category", y=["Estimated", "Actual"], barmode="group", title="Cost Comparison by Category")
st.plotly_chart(fig3, use_container_width=True)

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
# 📊 Biểu đồ Cột: Final Comparison (USD)
# 👉 Tạo bản sao để vẽ biểu đồ trước khi định dạng thành chuỗi
final_df_plot = final_df.copy()

# 👉 Loại bỏ dòng phần trăm vì không phải giá trị USD
final_df_plot = final_df_plot[~final_df_plot["Item"].str.contains(r"Gap \(%\)")]

# 👉 Chuyển cột Value về số để vẽ biểu đồ
final_df_plot["Value (USD)"] = final_df_plot["Value (USD)"].astype(float)

fig_final = px.bar(
    final_df_plot,
    x="Item", y="Value (USD)",
    title="Final Cost Comparison (USD)",
    text=final_df_plot["Value (USD)"].apply(lambda x: f"${x:,.2f}"),
    color="Value (USD)",
    color_continuous_scale="Blues"
)
fig_final.update_traces(textposition="outside")
fig_final.update_layout(
    xaxis_title="",
    yaxis_title="USD",
    uniformtext_minsize=8,
    uniformtext_mode='hide',
    margin=dict(t=60, b=40),
    height=420
)

# 🖼️ Hiển thị biểu đồ
st.plotly_chart(fig_final, use_container_width=True)

# 🔢 Format final values
final_df["Value (USD)"] = final_df.apply(
    lambda row: f"{row['Value (USD)']:.2f}%" if "Gap (%)" in row["Item"]
    else f"${row['Value (USD)']:,.2f}",
    axis=1
)
st.dataframe(final_df, use_container_width=True)

# === Fixed Unit Cost Info ===
st.markdown("### 4. Fixed Unit Costs (USD/hour)")
st.write(f"👷 Labor - Worker: ${LABOR_COST_WORKER:,.2f} | 🧑‍💼 Office: ${LABOR_COST_OFFICE:,.2f}")
st.write("🛠️ Machine Rates:")
for machine, cost in MACHINE_COST.items():
    st.write(f"- {machine}: ${cost:,.2f} per hour")
st.markdown("### 📥 Export Report")

# Tạo Excel file trong bộ nhớ
output = io.BytesIO()
wb = Workbook()

# === Sheet 1: Project Info ===
ws_info = wb.active
ws_info.title = "Project Info"
ws_info.append(["Project Name", project_name])
ws_info.append(["Start Date", start_date.strftime("%Y-%m-%d")])
ws_info.append(["End Date", end_date.strftime("%Y-%m-%d")])

# === Sheet 2: Summary Table ===
ws_summary = wb.create_sheet("Cost Summary")
for r in dataframe_to_rows(summary_df, index=False, header=True):
    ws_summary.append(r)

# === Sheet 3: Final Comparison ===
ws_final = wb.create_sheet("Final Comparison")
for r in dataframe_to_rows(final_df, index=False, header=True):
    ws_final.append(r)

wb.save(output)
output.seek(0)

# Tải file Excel
st.download_button(
    label="📤 Download Excel Report",
    data=output,
    file_name=f"{project_name.replace(' ', '_')}_report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
# 1. Biểu đồ cột: Cost Comparison
bar_chart_path = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
plt.figure(figsize=(8, 5))
df_bar = pd.DataFrame({
    "Category": list(est_cost.keys()),
    "Estimated": list(est_cost.values()),
    "Actual": [act_cost[k] for k in est_cost.keys()]
})
df_bar.set_index("Category").plot(kind='bar')
plt.title("Cost Comparison by Category")
plt.ylabel("USD")
plt.tight_layout()
plt.savefig(bar_chart_path)
plt.close()

# 2. Biểu đồ tròn: Estimated Cost Composition
pie1_path = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
if sum(est_cost.values()) > 0:
    plt.figure(figsize=(5, 5))
    plt.pie(list(est_cost.values()), labels=list(est_cost.keys()), autopct='%1.1f%%')
    plt.title("Estimated Cost Composition")
    plt.tight_layout()
    plt.savefig(pie1_path)
    plt.close()

# 3. Biểu đồ tròn: Actual Cost Composition
pie2_path = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
if sum(act_cost.values()) > 0:
    plt.figure(figsize=(5, 5))
    plt.pie(list(act_cost.values()), labels=list(act_cost.keys()), autopct='%1.1f%%')
    plt.title("Actual Cost Composition")
    plt.tight_layout()
    plt.savefig(pie2_path)
    plt.close()
    
# === Tạo PDF với biểu đồ

pdf = FPDF(orientation='P', unit='mm', format='A4')
pdf.add_page()

# Thêm logo nếu tồn tại
logo_path = "triac_logo.png"
if os.path.exists(logo_path):
    pdf.image(logo_path, x=10, y=10, w=40)
    pdf.ln(25)  # đẩy nội dung xuống tránh đè lên logo

# === Tiêu đề và Thông tin
pdf.set_font("Arial", 'B', 14)
pdf.cell(0, 10, "Project Cost Summary Report", ln=True)

pdf.set_font("Arial", '', 12)
pdf.cell(0, 10, f"Project: {project_name}", ln=True)
pdf.cell(0, 10, f"Duration: {start_date} to {end_date}", ln=True)
pdf.ln(5)

# === Final Summary
pdf.set_font("Arial", 'B', 12)
pdf.cell(0, 10, "Final Summary", ln=True)
pdf.set_font("Arial", '', 11)
for idx, row in final_df.iterrows():
    pdf.cell(0, 8, f"{row['Item']}: {row['Value (USD)']}", ln=True)

# === Charts Section (matplotlib)
pdf.ln(5)
pdf.set_font("Arial", 'B', 12)
pdf.cell(0, 10, "Charts", ln=True)

pdf.image(bar_chart_path, w=180)
if os.path.exists(pie1_path) and os.path.getsize(pie1_path) > 0:
    pdf.image(pie1_path, x=10, w=90)
if os.path.exists(pie2_path) and os.path.getsize(pie2_path) > 0:
    pdf.image(pie2_path, x=110, w=90)

# === Convert Plotly charts to images
diff_chart_path = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
final_chart_path = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name

pio.write_image(fig_diff, diff_chart_path, format='png', width=800, height=500)
pio.write_image(fig_final, final_chart_path, format='png', width=800, height=500)

# === Add Plotly charts to PDF
pdf.add_page()
pdf.set_font("Arial", 'B', 12)
pdf.cell(0, 10, "Review Charts", ln=True)

if os.path.exists(diff_chart_path):
    pdf.image(diff_chart_path, w=180)

if os.path.exists(final_chart_path):
    pdf.ln(5)
    pdf.image(final_chart_path, w=180)

# === Xuất ra file PDF để tải về
pdf_output = io.BytesIO()
pdf_bytes = pdf.output(dest='S').encode('latin-1')
pdf_output = io.BytesIO(pdf_bytes)
pdf_output.seek(0)

# === Nút tải file PDF
st.download_button(
    label="📄 Download PDF Report (with Charts)",
    data=pdf_output,
    file_name=f"{project_name.replace(' ', '_')}_report.pdf",
    mime="application/pdf"
)
