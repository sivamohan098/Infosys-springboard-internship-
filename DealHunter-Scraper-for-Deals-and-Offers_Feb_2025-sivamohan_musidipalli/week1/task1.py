# -*- coding: utf-8 -*-

import pandas as pd
import streamlit as st
import requests
from bs4 import BeautifulSoup
import io  # Import io for in-memory file handling

# Function to scrape data for a given state URL using BeautifulSoup
def scrape_table(state_url):
    try:
        # Send a GET request to the URL
        response = requests.get(state_url)
        if response.status_code != 200:
            st.error(f"Failed to fetch data from {state_url}")
            return pd.DataFrame()

        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.content, "html.parser")

        # Find the table (update the selector based on the website's HTML structure)
        table = soup.find("table")
        if not table:
            st.error("No table found on the page.")
            return pd.DataFrame()

        # Find all rows in the table body
        rows = table.find_all("tr")
        data = []

        for row in rows:
            cols = [col.get_text(strip=True) for col in row.find_all("td")]
            if cols:  # Only append rows with data (skip header rows)
                data.append(cols)

        # Define column names dynamically based on max columns
        max_cols = max(len(row) for row in data) if data else 5
        columns = ["City", "Library", "Address", "Zip", "Phone"][:max_cols]

        return pd.DataFrame(data, columns=columns)

    except Exception as e:
        st.error(f"An error occurred: {e}")
        return pd.DataFrame()

# Streamlit UI
st.title("Public Libraries Data")
st.write("Select a state to view its public libraries information.")

# List of states and their corresponding URLs
states = {
    "Alabama": "https://publiclibraries.com/state/alabama/",
    "Alaska": "https://publiclibraries.com/state/alaska/",
    "Arizona": "https://publiclibraries.com/state/arizona/",
    "Arkansas": "https://publiclibraries.com/state/arkansas/",
    "California": "https://publiclibraries.com/state/california/",
    "Colorado": "https://publiclibraries.com/state/colorado/",
    "Connecticut": "https://publiclibraries.com/state/connecticut/",
    "Delaware": "https://publiclibraries.com/state/delaware/",
    "Florida": "https://publiclibraries.com/state/florida/",
    "Georgia": "https://publiclibraries.com/state/georgia/",
    "Hawaii": "https://publiclibraries.com/state/hawaii/",
    "Idaho": "https://publiclibraries.com/state/idaho/",
    "Illinois": "https://publiclibraries.com/state/illinois/",
    "Indiana": "https://publiclibraries.com/state/indiana/",
    "Iowa": "https://publiclibraries.com/state/iowa/",
    "Kansas": "https://publiclibraries.com/state/kansas/",
    "Kentucky": "https://publiclibraries.com/state/kentucky/",
    "Louisiana": "https://publiclibraries.com/state/louisiana/",
    "Maine": "https://publiclibraries.com/state/maine/",
    "Maryland": "https://publiclibraries.com/state/maryland/",
    "Massachusetts": "https://publiclibraries.com/state/massachusetts/",
    "Michigan": "https://publiclibraries.com/state/michigan/",
    "Minnesota": "https://publiclibraries.com/state/minnesota/",
    "Mississippi": "https://publiclibraries.com/state/mississippi/",
    "Missouri": "https://publiclibraries.com/state/missouri/",
    "Montana": "https://publiclibraries.com/state/montana/",
    "Nebraska": "https://publiclibraries.com/state/nebraska/",
    "Nevada": "https://publiclibraries.com/state/nevada/",
    "New Hampshire": "https://publiclibraries.com/state/new-hampshire/",
    "New Jersey": "https://publiclibraries.com/state/new-jersey/",
    "New Mexico": "https://publiclibraries.com/state/new-mexico/",
    "New York": "https://publiclibraries.com/state/new-york/",
    "North Carolina": "https://publiclibraries.com/state/north-carolina/",
    "North Dakota": "https://publiclibraries.com/state/north-dakota/",
    "Ohio": "https://publiclibraries.com/state/ohio/",
    "Oklahoma": "https://publiclibraries.com/state/oklahoma/",
    "Oregon": "https://publiclibraries.com/state/oregon/",
    "Pennsylvania": "https://publiclibraries.com/state/pennsylvania/",
    "Rhode Island": "https://publiclibraries.com/state/rhode-island/",
    "South Carolina": "https://publiclibraries.com/state/south-carolina/",
    "South Dakota": "https://publiclibraries.com/state/south-dakota/",
    "Tennessee": "https://publiclibraries.com/state/tennessee/",
    "Texas": "https://publiclibraries.com/state/texas/",
    "Utah": "https://publiclibraries.com/state/utah/",
    "Vermont": "https://publiclibraries.com/state/vermont/",
    "Virginia": "https://publiclibraries.com/state/virginia/",
    "Washington": "https://publiclibraries.com/state/washington/",
    "West Virginia": "https://publiclibraries.com/state/west-virginia/",
    "Wisconsin": "https://publiclibraries.com/state/wisconsin/",
    "Wyoming": "https://publiclibraries.com/state/wyoming/"
}

# Dropdown to select a state
selected_state = st.selectbox("Select a state", list(states.keys()))

if st.button("Fetch Data"):
    state_url = states[selected_state]
    df = scrape_table(state_url)

    if not df.empty:
        st.dataframe(df)

        # Download buttons
        st.download_button(
            label="Download as CSV",
            data=df.to_csv(index=False),
            file_name=f"{selected_state}_libraries.csv",
            mime="text/csv"
        )
        st.download_button(
            label="Download as JSON",
            data=df.to_json(orient="records"),
            file_name=f"{selected_state}_libraries.json",
            mime="application/json"
        )

        # Create an in-memory Excel file using openpyxl
        excel_file = io.BytesIO()
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        excel_file.seek(0)  # Reset the stream position to the beginning

        st.download_button(
            label="Download as Excel",
            data=excel_file,
            file_name=f"{selected_state}_libraries.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("No data found for this state.")