import streamlit as st
import pdfplumber
import pandas as pd
import os
import re
from datetime import datetime

st.set_page_config(page_title="🩺 Medical Report Chatbot", layout="centered")
st.title("🩺 Medical Report Chatbot")
st.write("Upload your blood test report in PDF format and get a summary.")

# Simulated previous data for comparison (in real use, fetch from database)
previous_data = {
    "Hemoglobin": {"value": 13.2, "date": "2024-12-15"},
    "WBC Count": {"value": 8900, "date": "2024-12-15"},
    "Platelet Count": {"value": 180000, "date": "2024-12-15"},
    "Fasting Blood Sugar": {"value": 125, "date": "2024-12-15"},
    "Cholesterol": {"value": 175, "date": "2024-12-15"},
    "Triglyceride": {"value": 145, "date": "2024-12-15"},
}

def extract_tests_from_text(text):
    test_pattern = re.compile(
        r"(?P<Test>[A-Za-z0-9\-()/%\s]+?)\s+(?P<Result>[<>]?[\d.]+)\s+(?P<Unit>\S+)\s+(?P<RefLow>[\d.]+)\s*[-–]\s*(?P<RefHigh>[\d.]+)",
        re.MULTILINE
    )

    data = []
    for match in test_pattern.finditer(text):
        test_name = match.group("Test").strip()
        result_str = match.group("Result").replace("<", "").replace(">", "").strip()

        try:
            result = float(result_str)
            ref_low = float(match.group("RefLow"))
            ref_high = float(match.group("RefHigh"))

            if result < ref_low:
                status = "Low"
            elif result > ref_high:
                status = "High"
            else:
                status = "Normal"

            prev_info = previous_data.get(test_name, {})
            prev_value = prev_info.get("value")
            prev_date = prev_info.get("date")
            change = result - prev_value if prev_value is not None else None

            data.append({
                "Test": test_name,
                "Previous Value": prev_value,
                "Previous Date": prev_date,
                "Current Value": result,
                "Change": change,
                "Unit": match.group("Unit"),
                "Reference Range": f"{ref_low} - {ref_high}",
                "Status": status
            })
        except ValueError:
            continue

    return pd.DataFrame(data)

uploaded_file = st.file_uploader("📤 Upload PDF Report", type=["pdf"])

if uploaded_file:
    os.makedirs("sample_reports", exist_ok=True)
    os.makedirs("excel_outputs", exist_ok=True)

    save_path = os.path.join("sample_reports", uploaded_file.name)
    with open(save_path, "wb") as f:
        f.write(uploaded_file.read())

    st.success("✅ Report uploaded successfully!")
    st.write("🔍 Extracting data...")

    with pdfplumber.open(save_path) as pdf:
        all_text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())

    if all_text:
        st.text_area("📄 Extracted Text", all_text[:3000], height=250)
        df = extract_tests_from_text(all_text)

        if not df.empty:
            st.dataframe(df, use_container_width=True)

            timestamp = datetime.today().strftime("%Y-%m-%d_%H-%M")
            excel_filename = f"report_summary_{timestamp}.xlsx"
            excel_path = os.path.join("excel_outputs", excel_filename)

            with pd.ExcelWriter(excel_path, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name="Report")
                workbook = writer.book
                worksheet = writer.sheets["Report"]

                red_format = workbook.add_format({'font_color': 'red'})
                yellow_format = workbook.add_format({'font_color': 'orange'})

                current_col = df.columns.get_loc("Current Value")

                for row_num, status in enumerate(df["Status"], start=1):
                    value = df.loc[row_num - 1, "Current Value"]
                    if status == "High":
                        worksheet.write(row_num, current_col, value, red_format)
                    elif status == "Low":
                        worksheet.write(row_num, current_col, value, yellow_format)

            st.success("📁 Excel report saved.")
            with open(excel_path, "rb") as f:
                st.download_button("⬇️ Download Excel", f, file_name=f"Medical_Report_{timestamp}.xlsx")
                st.code(f"📁 Saved at: {excel_path}")
        else:
            st.warning("⚠️ No valid test data found.")
    else:
        st.error("❌ No text could be extracted from the PDF.")
