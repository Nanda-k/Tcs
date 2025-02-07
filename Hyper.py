import streamlit as st
import pandas as pd
import requests
from st_aggrid import AgGrid, GridOptionsBuilder

st.set_page_config(layout='wide')

# ✅ TIMS Drug list
drugs = pd.DataFrame({
    "Drug name": [
        "abatacept", "abrocitinib", "adalimumab", "alemtuzumab", "anakinra", 
        "apremilast", "baricitinib", "benralizumab", "brodalumab", "canakinumab",
        "certolizumab pegol", "deucravacitinib", "deuruxolitinib", "dupilumab", 
        "etanercept", "etrasimod", "golimumab", "guselkumab", "infliximab", 
        "ixekizumab", "mepolizumab", "mirikizumab-mrkz", "natalizumab", 
        "ocrelizumab", "ofatumumab", "omalizumab", "ozanimod", "reslizumab", 
        "risankizumab", "rituximab", "roflumilast", "ruxolitinib", "sarilumab", 
        "secukinumab", "spesolimab-sbzo", "tezepelumab ekko", "tildrakizumab-asmn", 
        "tocilizumab", "tocilizumab bavi", "tocilizumab aazg", "tofacitinib", 
        "tralokinumab", "upadacitinib", "ustekinumab", "vedolizumab"
    ]
})

# ✅ Fetch Clinical Trials Data
def fetch_clinical_trials(drug_name):
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    params = {
        'query.term': drug_name,
        'pageSize': 100,
        'format': 'json'
    }
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Raise exception for bad responses
        data = response.json()
        studies = data.get('studies', [])

        # ✅ Extract required fields
        records = []
        for study in studies:
            protocol_section = study.get('protocolSection', {})
            identification_module = protocol_section.get('identificationModule', {})
            status_module = protocol_section.get('statusModule', {})
            conditions_module = protocol_section.get('conditionsModule', {})
            design_module = protocol_section.get('designModule', {})

            nct_id = identification_module.get('nctId', 'N/A')
            title = identification_module.get('briefTitle', 'N/A')

            # ✅ Create proper hyperlink for each title
            title_link = f"https://clinicaltrials.gov/study/{nct_id}?term={nct_id}&rank=1"

            record = {
                'Drug Name': drug_name,  # ✅ NEW Identifier Column
                'NCT ID': nct_id,
                'Title': title,  # ✅ Displayed text
                'Title Link': title_link,  # ✅ Hyperlink URL
                'Status': status_module.get('overallStatus', 'N/A'),
                'Start Date': status_module.get('startDateStruct', {}).get('date', 'N/A'),
                'Completion Date': status_module.get('completionDateStruct', {}).get('date', 'N/A'),
                'Conditions': ', '.join(conditions_module.get('conditions', [])),
                'Study Type': design_module.get('studyType', 'N/A'),
                'Phase': ', '.join(design_module.get('phases', [])),
                'Enrollment': design_module.get('enrollmentInfo', {}).get('count', 'N/A')
            }
            records.append(record)

        return pd.DataFrame(records)

    except requests.exceptions.RequestException as e:
        st.error(f"⚠️ Failed to fetch clinical trials for **{drug_name}**. Error: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Unexpected error while fetching trials for **{drug_name}**: {e}")
        return pd.DataFrame()


# ✅ Run Streamlit App
def run_app():
    st.title("📌 Drug Database & Clinical Trials Lookup")
    
    # 🔹 Search bar for drugs
    selected_drugs = st.multiselect(
        "🔍 Search for Drugs:",
        options=drugs["Drug name"].tolist(),
        default=[]
    )

    # 🔹 Create Tabs for Data Sections
    tab1, tab2, tab3 = st.tabs(["📌 RxNorm", "📑 Clinical Trials", "⚕️ OpenFDA"])

    # ✅ Clinical Trials Tab
    with tab2:
        if selected_drugs:
            all_clinical_trials = []
            for drug in selected_drugs:
                clinical_trials = fetch_clinical_trials(drug)
                if not clinical_trials.empty:
                    all_clinical_trials.append(clinical_trials)

            if all_clinical_trials:
                clinical_trials_df = pd.concat(all_clinical_trials, ignore_index=True)

                # ✅ Create unique list of conditions
                all_conditions = set(
                    condition.strip() 
                    for conditions in clinical_trials_df["Conditions"].dropna() 
                    for condition in conditions.split(",")
                )

                # 🔹 Sidebar Filters
                col1, col2, col3 = st.columns([1, 1, 1])

                with col1:
                    # ✅ Filter by Study Status
                    status_filter = st.selectbox(
                        "📌 Filter by Study Status:",
                        options=["All"] + sorted(clinical_trials_df["Status"].dropna().unique().tolist())
                    )

                with col2:
                    # ✅ Filter by Conditions
                    condition_filter = st.multiselect(
                        "📌 Filter by Conditions:",
                        options=["All"] + sorted(all_conditions),
                        default=["All"]
                    )

                with col3:
                    # ✅ Clear Filters Button
                    if st.button("Reset Filters"):
                        status_filter = "All"
                        condition_filter = ["All"]

                # ✅ Apply Status filter
                filtered_trials_df = clinical_trials_df
                if status_filter != "All":
                    filtered_trials_df = filtered_trials_df[filtered_trials_df["Status"] == status_filter]

                # ✅ Apply Condition filter
                if "All" not in condition_filter:
                    filtered_trials_df = filtered_trials_df[
                        filtered_trials_df["Conditions"].apply(
                            lambda x: any(cond.strip() in condition_filter for cond in x.split(","))
                        )
                    ]

                # ✅ Display Filtered Data using AgGrid
                st.write("### 📑 Clinical Trials Data")

                # ✅ Configure AgGrid with Clickable Links
                gb = GridOptionsBuilder.from_dataframe(filtered_trials_df)
                gb.configure_default_column(resizable=True, wrapText=True, autoHeight=True)

                # ✅ Enable HTML rendering for "Title"
                gb.configure_column("Title", cellRenderer="""
                    function(params) {
                        return `<a href="${params.data['Title Link']}" target="_blank" style="color: #00C7FF; text-decoration: underline;">${params.value}</a>`;
                    }
                """)

                grid_options = gb.build()

                AgGrid(
                    filtered_trials_df,
                    gridOptions=grid_options,
                    enable_enterprise_modules=False,
                    allow_unsafe_jscode=True,
                    height=500,  # Adjust for better viewing
                    fit_columns_on_grid_load=False,  # Prevent auto-resizing that hides columns
                )

                # ✅ Download Button
                st.download_button(
                    label="📥 Download Clinical Trials Data",
                    data=filtered_trials_df.to_csv(index=False),
                    file_name="clinical_trials_data.csv",
                    mime="text/csv"
                )
            else:
                st.warning("⚠️ No clinical trials data found for the selected drugs.")
        else:
            st.warning("🔍 Please select drugs to fetch Clinical Trials data.")

if __name__ == "__main__":
    run_app()
