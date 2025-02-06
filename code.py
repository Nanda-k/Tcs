import streamlit as st
import pandas as pd
import requests
from st_aggrid import AgGrid, GridOptionsBuilder

st.set_page_config(layout='wide')

# TIMS Drug list
tims = pd.DataFrame({
    "Drug name": ["abatacept", "abrocitinib", "adalimumab", "alemtuzumab", "anakinra", "apremilast", "baricitinib", "benralizumab", "brodalumab", "canakinumab",
    "certolizumab pegol", "deucravacitinib", "deuruxolitinib", "dupilumab", "etanercept", "etrasimod", "golimumab", "guselkumab", "infliximab", "ixekizumab",
    "mepolizumab", "mirikizumab-mrkz", "natalizumab", "ocrelizumab", "ofatumumab", "omalizumab", "ozanimod", "reslizumab", "risankizumab", "rituximab", "roflumilast",
    "ruxolitinib", "sarilumab", "secukinumab", "spesolimab-sbzo", "tezepelumab ekko", "tildrakizumab-asmn", "tocilizumab", "tocilizumab bavi", "tocilizumab aazg",
    "tofacitinib", "tralokinumab", "upadacitinib", "ustekinumab", "vedolizumab"]
})

def fetch_rxcui(drug_name):
    url = f"https://rxnav.nlm.nih.gov/REST/rxcui.json?name={drug_name}"
    response = requests.get(url)
    if response.status_code != 200:
        return None
    data = response.json()
    return data.get("idGroup", {}).get("rxnormId", [None])[0]

def fetch_brand_names(rxcui, drug_name):
    url = f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/allrelated.json"
    response = requests.get(url)
    brands = []
    if response.status_code == 200:
        data = response.json()
        for group in data.get("allRelatedGroup", {}).get("conceptGroup", []):
            if group.get("tty") == "BN":  # BN = Brand Name
                for concept in group.get("conceptProperties", []):
                    brands.append({"Drug Name": drug_name, "Brand Name": concept.get("name", "N/A")})
    return pd.DataFrame(brands).drop_duplicates()

def fetch_moa(rxcui, drug_name):
    url = f"https://rxnav.nlm.nih.gov/REST/rxclass/class/byRxcui.json?rxcui={rxcui}&rela=has_mechanism_of_action&classTypes=MOA"
    response = requests.get(url)
    moa = []
    if response.status_code == 200:
        data = response.json()
        for entry in data.get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", []):
            moa.append({"Drug Name": drug_name,
                "Mechanism of Action": entry.get("rxclassMinConceptItem", {}).get("className", "N/A"),
                "Class Type": entry.get("rxclassMinConceptItem", {}).get("classType", "N/A")
            })
    return pd.DataFrame(moa).drop_duplicates()

def fetch_indications(rxcui, drug_name):
    url = f"https://rxnav.nlm.nih.gov/REST/rxclass/class/byRxcui.json?rxcui={rxcui}&rela=may_treat&classTypes=DISEASE"
    response = requests.get(url)
    indications = []
    if response.status_code == 200:
        data = response.json()
        for entry in data.get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", []):
            indications.append({"Drug Name": drug_name,
                "Indication": entry.get("rxclassMinConceptItem", {}).get("className", "N/A"),
                "Class Type": entry.get("rxclassMinConceptItem", {}).get("classType", "N/A")
            })
    return pd.DataFrame(indications).drop_duplicates()

def fetch_therapeutic_class(rxcui, drug_name):
    url = f"https://rxnav.nlm.nih.gov/REST/rxclass/class/byRxcui.json?rxcui={rxcui}&rela=has_therapeutic_class&classTypes=ATC1-4,VA"
    response = requests.get(url)
    therapeutic_classes = []
    if response.status_code == 200:
        data = response.json()
        for entry in data.get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", []):
            therapeutic_classes.append({"Drug Name": drug_name,
                "Therapeutic Class": entry.get("rxclassMinConceptItem", {}).get("className", "N/A"),
                "Class Type": entry.get("rxclassMinConceptItem", {}).get("classType", "N/A")
            })
    return pd.DataFrame(therapeutic_classes).drop_duplicates()

# Therapeutic Class Drug Mapping
tc_data = pd.read_csv('tc_tims.csv')
tc_to_drugs = tc_data.groupby("Therapeutic Class")["Drug Name"].apply(lambda x: ", ".join(set(x))).to_dict()

def display_therapeutic_classes_with_tooltip(df):
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(groupable=True, value=True, enableRowGroup=True)

    # ✅ Ensure Tooltip Field is Correct
    df["Tooltip"] = df["Therapeutic Class"].map(tc_to_drugs)

    # ✅ Properly Format the Tooltip as Plain Text
    def format_tooltip_text(text):
        if pd.isna(text) or text == "":
            return ""  # Handle missing values safely
        drugs = text.split(", ")  # Split by comma
        return "\n".join(drugs)  # Use newline for formatting

    df["Tooltip"] = df["Tooltip"].apply(format_tooltip_text)

    # ✅ Configure Tooltip Column with Plain Text Rendering
    gb.configure_column(
        "Therapeutic Class",
        tooltipField="Tooltip"
    )

    # ✅ Additional Grid Configurations
    grid_options = gb.build()
    grid_options["tooltipShowDelay"] = 0  # Show tooltip instantly
    grid_options["tooltipHideDelay"] = 10000  # Keep tooltip visible for 10 seconds
    grid_options["suppressSizeToFit"] = False  # Prevent tooltip from being cut off

    # ✅ Apply Custom CSS for Tooltips (No HTML Needed)
    custom_css = {
        ".ag-tooltip": {
            "font-size": "18px",  # ✅ Increased Font Size
            "background-color": "#f0f0f0",  # ✅ Light Gray Background
            "color": "black",  # ✅ Black Text for Readability
            "padding": "10px",
            "border-radius": "8px",
            "max-width": "300px",
            "white-space": "pre-wrap",  # ✅ Ensures Proper Line Breaks
            "text-align": "left"
        }
    }

    # ✅ Display AgGrid with Properly Styled Tooltips (No HTML)
    AgGrid(
        df,
        gridOptions=grid_options,
        enable_enterprise_modules=True,
        allow_unsafe_jscode=True,
        height=500,
        fit_columns_on_grid_load=True,
        custom_css=custom_css  # ✅ Applying tooltip styling
    )
 
def fetch_drug_details(drug_name):
    rxcui = fetch_rxcui(drug_name)
    if not rxcui:
        return None

    details = {
        "Brand Names": fetch_brand_names(rxcui, drug_name),
        "Mechanism of Action": fetch_moa(rxcui, drug_name),
        "Indications": fetch_indications(rxcui, drug_name),
        "Therapeutic Class": fetch_therapeutic_class(rxcui, drug_name)
    }
    return details

def run_app():
    st.title("Drug Database")
    selected_drugs = st.multiselect("Search for Drugs:", options=tims["Drug name"].tolist(), default=[])

    if st.button("Search"):
        if selected_drugs:
            all_therapeutic_classes = []

            for drug_name in selected_drugs:
                details = fetch_drug_details(drug_name.strip())
                if details:
                    all_therapeutic_classes.append(details["Therapeutic Class"])

            all_therapeutic_classes_df = pd.concat(all_therapeutic_classes, ignore_index=True)
            all_therapeutic_classes_df = all_therapeutic_classes_df.sort_values(by="Drug Name").reset_index(drop=True)

            st.subheader("Therapeutic Classes with Tooltips")
            display_therapeutic_classes_with_tooltip(all_therapeutic_classes_df)

        else:
            st.error("Please select at least one drug to search.")

if __name__ == "__main__":
    run_app()
