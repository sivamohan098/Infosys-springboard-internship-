import streamlit as st
from streamlit_tags import st_tags_sidebar
import pandas as pd
import json
from datetime import datetime

from scraper import (
    fetch_html_selenium, 
    save_raw_data, 
    format_data, 
    save_formatted_data, 
    calculate_price, 
    html_to_markdown_with_readability, 
    create_dynamic_listing_model, 
    create_listings_container_model,
    PRICING
)

st.set_page_config(page_title="Universal Web Scraper 🌏")
st.title("Universal Web Scraper 🌏")

st.sidebar.title("Web Scraper Settings 🛠️ ⚙️")
model_selection = st.sidebar.selectbox(
    "Select Model", 
    options=list(PRICING.keys()),  # e.g. ["openai-gpt-3.5", "gemini-2.0-flash", "groq-llama"]
    index=0
)
url_input = st.sidebar.text_input("Enter URL HERE")

fields = st_tags_sidebar(
    label='Fields to Extract:',
    text='enter to add a tag',
    value=["deal name","product name","price","discount"],  # example default
    suggestions=[],
    maxtags=-1,
    key='tags_input'
)

def perform_scrape():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    st.write("**DEBUG**: Starting `perform_scrape`...")

    # 1) Scrape raw HTML
    st.write("**DEBUG**: Fetching HTML with Selenium from:", url_input)
    raw_html = fetch_html_selenium(url_input)

    # 2) Convert to markdown
    st.write("**DEBUG**: Converting HTML to Markdown...")
    markdown = html_to_markdown_with_readability(raw_html)
    save_raw_data(markdown, timestamp)

    # 3) Create dynamic Pydantic models
    st.write("**DEBUG**: Creating dynamic Pydantic models from fields:", fields)
    DynamicListingModel = create_dynamic_listing_model(fields)
    DynamicListingsContainer = create_listings_container_model(DynamicListingModel)

    # 4) Format data (calls one of the LLMs with chunking)
    st.write("**DEBUG**: Formatting data with model:", model_selection)
    formatted_data, tokens_count = format_data(
        data=markdown, 
        ContainerModel=DynamicListingsContainer, 
        ListingModel=DynamicListingModel, 
        selected_model=model_selection,
        fields=fields
    )

    # 5) Calculate token usage
    st.write("**DEBUG**: Calculating token usage...")
    input_tokens, output_tokens, total_cost = calculate_price(tokens_count, model=model_selection)

    # 6) Save final data (returns a DataFrame)
    st.write("**DEBUG**: Saving final data, building DataFrame...")
    df = save_formatted_data(formatted_data, timestamp)

    if df is not None:
        print(f"PERFORM_SCRAPE DEBUG: df.shape after saving = {df.shape}")
    else:
        print("PERFORM_SCRAPE DEBUG: df is None!")

    st.write("**DEBUG**: Done. Returning DF, etc.")
    return df, formatted_data, markdown, input_tokens, output_tokens, total_cost, timestamp

if 'perform_scrape' not in st.session_state:
    st.session_state['perform_scrape'] = False

if st.sidebar.button("click Scrape"):
    with st.spinner('Scraping in progress...'):
        st.session_state['results'] = perform_scrape()
        st.session_state['perform_scrape'] = True

if st.session_state.get('perform_scrape'):
    st.write("**DEBUG**: We have `perform_scrape` = True, so let's unpack results.")
    df, formatted_data, markdown, input_tokens, output_tokens, total_cost, timestamp = st.session_state['results']

    if df is None:
        st.error("The DataFrame (df) is None. Possibly no data extracted.")
    else:
        st.write("**DEBUG**: df.shape =", df.shape)
        st.write(df.head(5))  # show first 5 rows for debugging
        st.write("### Scraped Data (Full):")
        st.dataframe(df)

    st.sidebar.markdown("**Token Usage**")
    st.sidebar.markdown(f"Input Tokens: {input_tokens}")
    st.sidebar.markdown(f"Output Tokens: {output_tokens}")
    st.sidebar.markdown(f"Total Cost: :green[${total_cost:.4f}]")

    # Provide download buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        try:
            if isinstance(formatted_data, str):
                data_dict = json.loads(formatted_data)
            else:
                data_dict = formatted_data.dict() if hasattr(formatted_data, 'dict') else formatted_data
        except json.JSONDecodeError:
            st.warning("Warning: The final data is invalid JSON. Falling back to empty data.")
            data_dict = {"listings": []}

        st.download_button(
            "JSON Format",
            data=json.dumps(data_dict, indent=4),
            file_name=f"{timestamp}_data.json"
        )

    with col2:
        if isinstance(data_dict, dict) and "listings" in data_dict:
            main_data = data_dict["listings"]
        else:
            main_data = data_dict

        try:
            csv_df = pd.DataFrame(main_data)
        except Exception as e:
            st.warning(f"Could not convert data to DataFrame: {e}")
            csv_df = pd.DataFrame()

        st.download_button(
            "CSV Format",
            data=csv_df.to_csv(index=False),
            file_name=f"{timestamp}_data.csv"
        )

    with col3:
        st.download_button(
            "Markdown Format",
            data=markdown,
            file_name=f"{timestamp}_data.md"
        )

    # Optionally show leftover text if invalid JSON
    # if isinstance(data_dict, dict) and "raw_text" in data_dict:
    #     st.write("**Partial leftover text**:", data_dict["raw_text"])
