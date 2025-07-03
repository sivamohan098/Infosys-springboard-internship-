# app.py
import sys
import asyncio
if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import streamlit as st
from streamlit_tags import st_tags_sidebar
import pandas as pd
import json
from datetime import datetime

from scraper import (
    fetch_html_playwright,
    save_raw_data,
    format_data,
    save_formatted_data,
    calculate_price,
    html_to_markdown_with_readability,
    create_dynamic_listing_model,
    create_listings_container_model
)
from assets import PRICING
import chunk_processor

# ---------------------
# JSON Fix Helpers
# ---------------------
def balance_json_string(broken_json_str: str) -> str:
    open_brace = broken_json_str.count('{')
    close_brace = broken_json_str.count('}')
    open_bracket = broken_json_str.count('[')
    close_bracket = broken_json_str.count(']')
    if open_brace > close_brace:
        broken_json_str += "}" * (open_brace - close_brace)
    if open_bracket > close_bracket:
        broken_json_str += "]" * (open_bracket - close_bracket)
    return broken_json_str

def best_effort_json_fix(broken_json_str: str):
    balanced = balance_json_string(broken_json_str)
    try:
        return json.loads(balanced)
    except json.JSONDecodeError:
        return None

# ---------------------
# Process in Overlapping Chunks
# ---------------------
def process_in_chunks(content: str, chunk_size: int = 3000, overlap: int = 300):
    chunks = []
    start = 0
    length = len(content)
    while start < length:
        end = min(length, start + chunk_size)
        chunk = content[start:end]
        chunks.append(chunk)
        start += (chunk_size - overlap)
    return chunks

# ---------------------
# Streamlit App
# ---------------------
st.set_page_config(page_title="Universal Web Scraper 🌏")
st.title("Universal Web Scraper 🌏")

st.sidebar.title("Web Scraper ⚙️")
model_selection = st.sidebar.selectbox("Select Model", options=list(PRICING.keys()), index=0)
url_input = st.sidebar.text_input("Enter URL")

chunk_size = st.sidebar.slider(
    "Chunk Size",
    min_value=1000,
    max_value=20000,
    value=3000,  # smaller default
    step=500
)
chunk_overlap = st.sidebar.slider(
    "Chunk Overlap",
    min_value=100,
    max_value=2000,
    value=300,   # smaller default
    step=100
)

tags = st.sidebar.empty()
tags = st_tags_sidebar(
    label='Enter Fields to Extract:',
    text='Press enter to add a tag',
    value=[],  # default empty
    suggestions=[],
    maxtags=-1,
    key='tags_input'
)
fields = tags

st.sidebar.markdown("---")

def perform_scrape():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    raw_html = loop.run_until_complete(fetch_html_playwright(url_input))
    markdown = html_to_markdown_with_readability(raw_html)
    save_raw_data(markdown, timestamp)

    DynamicListingModel = create_dynamic_listing_model(fields)
    DynamicListingsContainer = create_listings_container_model(DynamicListingModel)

    # Split markdown content into overlapping chunks
    chunks = process_in_chunks(markdown, chunk_size=chunk_size, overlap=chunk_overlap)
    combined_listings = []
    total_tokens = {"input_tokens": 0, "output_tokens": 0}

    for chunk in chunks:
        chunk_result, tokens_count = format_data(
            chunk,
            DynamicListingsContainer,
            DynamicListingModel,
            model_selection
        )
        if "listings" in chunk_result:
            combined_listings.extend(chunk_result["listings"])

        total_tokens["input_tokens"] += tokens_count.get("input_tokens", 0)
        total_tokens["output_tokens"] += tokens_count.get("output_tokens", 0)

    combined_data = {"listings": combined_listings}
    in_tokens, out_tokens, total_c = calculate_price(total_tokens, model=model_selection)
    df = save_formatted_data(combined_data, timestamp)
    return df, combined_data, markdown, in_tokens, out_tokens, total_c, timestamp

if 'perform_scrape' not in st.session_state:
    st.session_state['perform_scrape'] = False

if st.sidebar.button("Scrape"):
    with st.spinner('Please wait... Data is being scraped.'):
        st.session_state['results'] = perform_scrape()
        st.session_state['perform_scrape'] = True

if st.session_state.get('perform_scrape'):
    df, formatted_data, markdown, input_tokens, output_tokens, total_cost, timestamp = st.session_state['results']

    # Because of post-processing, we should always have address/phone, even if empty.
    # So "missing field" warnings should not appear now.

    st.write("Scraped Data:", df)

    st.sidebar.markdown("### Token Usage")
    st.sidebar.markdown(f"**Input Tokens:** {input_tokens}")
    st.sidebar.markdown(f"**Output Tokens:** {output_tokens}")
    st.sidebar.markdown(f"**Total Cost:** ${total_cost:.4f}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button(
            "Download JSON",
            data=json.dumps(formatted_data, indent=4),
            file_name=f"{timestamp}_data.json"
        )
    with col2:
        try:
            if "listings" in formatted_data:
                df_csv = pd.DataFrame(formatted_data["listings"])
            else:
                df_csv = pd.DataFrame({"raw_data": [formatted_data]})
            st.download_button(
                "Download CSV",
                data=df_csv.to_csv(index=False),
                file_name=f"{timestamp}_data.csv"
            )
        except Exception as e:
            st.error(f"Error converting data to CSV: {e}")

    with col3:
        st.download_button(
            "Download Markdown",
            data=markdown,
            file_name=f"{timestamp}_data.md"
        )

    st.markdown("## Gemini Chunk Processing")
    if st.button("Process Markdown with Gemini"):
        with st.spinner("Processing markdown in chunks..."):
            results = chunk_processor.process_markdown(markdown)
            table_output = chunk_processor.display_results_table(results)
            st.text_area("Gemini Responses Table", table_output, height=400)

if 'results' in st.session_state:
    df, formatted_data, markdown, input_tokens, output_tokens, total_cost, timestamp = st.session_state['results']
