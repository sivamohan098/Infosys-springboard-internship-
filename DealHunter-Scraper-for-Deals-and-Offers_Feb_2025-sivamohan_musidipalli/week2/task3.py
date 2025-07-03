# -*- coding: utf-8 -*-
import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
from io import BytesIO, StringIO
from urllib.parse import urljoin
import time

# Set page config
st.set_page_config(
    page_title="Web Scraper Pro",
    layout="wide",
    page_icon="🌐",
    menu_items={
        'About': "### Professional Web Scraping Suite\nCombine multiple scrapers in one interface!"
    }
)

# =============================================
# CUSTOM CSS STYLING
# =============================================

st.markdown("""
<style>
    /* Main container styling */
    .main {
        background: #f8f9fa;
        padding: 2rem 3rem;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(145deg, #2c3e50 0%, #3498db 100%) !important;
        padding: 1.5rem !important;
    }
    
    /* Title styling */
    h1 {
        color: #2c3e50;
        font-family: 'Poppins', sans-serif;
        border-bottom: 3px solid #4CAF50;
        padding-bottom: 0.5rem;
        margin-bottom: 2rem !important;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(45deg, #4CAF50, #45a049) !important;
        color: white !important;
        border-radius: 8px !important;
        padding: 0.75rem 2rem !important;
        transition: all 0.3s ease !important;
        border: none !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2) !important;
    }
    
    /* Dataframe styling */
    .stDataFrame {
        border-radius: 10px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
    }
    
    /* Download buttons container */
    .download-container {
        background: white !important;
        padding: 1.5rem !important;
        border-radius: 10px !important;
        margin-top: 2rem !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
    }
    
    /* Input field styling */
    .stTextInput input {
        border-radius: 8px !important;
        border: 1px solid #ddd !important;
        padding: 0.75rem 1rem !important;
    }
    
    /* Select box styling */
    .stSelectbox > div > div {
        border-radius: 8px !important;
        border: 1px solid #ddd !important;
    }
    
    /* Spinner animation */
    .stSpinner > div {
        border-color: #4CAF50 !important;
        border-right-color: transparent !important;
    }
</style>
""", unsafe_allow_html=True)

# Add custom font
st.markdown(
    """<link href='https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap' rel='stylesheet'>""",
    unsafe_allow_html=True
)

# =============================================
# PUBLIC LIBRARIES SCRAPER
# =============================================

def public_libraries_app():
    st.title("📚 Public Libraries Data Explorer")
    
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

    def scrape_table(state_url):
        try:
            response = requests.get(state_url)
            if response.status_code != 200:
                st.error(f"Failed to fetch data from {state_url}")
                return pd.DataFrame()

            soup = BeautifulSoup(response.content, "html.parser")
            table = soup.find("table")
            if not table:
                st.error("No table found on the page.")
                return pd.DataFrame()

            rows = table.find_all("tr")
            data = []
            for row in rows:
                cols = [col.get_text(strip=True) for col in row.find_all("td")]
                if cols:
                    data.append(cols)

            max_cols = max(len(row) for row in data) if data else 5
            columns = ["City", "Library", "Address", "Zip", "Phone"][:max_cols]
            return pd.DataFrame(data, columns=columns)

        except Exception as e:
            st.error(f"An error occurred: {e}")
            return pd.DataFrame()

    selected_state = st.selectbox("Select a state", list(states.keys()))
    
    if st.button("🚀 Fetch Library Data", type="primary"):
        with st.spinner("🔍 Scanning library databases..."):
            state_url = states[selected_state]
            df = scrape_table(state_url)

        if not df.empty:
            st.success(f"✅ Found {len(df)} libraries in {selected_state}!")
            st.dataframe(df, use_container_width=True)
            
            # Download Section
            st.markdown("---")
            st.subheader("📥 Download Options")
            cols = st.columns(3)
            with cols[0]:
                st.download_button(
                    label="Download CSV",
                    data=df.to_csv(index=False),
                    file_name=f"{selected_state}_libraries.csv",
                    mime="text/csv"
                )
            with cols[1]:
                excel_file = BytesIO()
                with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                excel_file.seek(0)
                st.download_button(
                    label="Download Excel",
                    data=excel_file,
                    file_name=f"{selected_state}_libraries.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            with cols[2]:
                st.download_button(
                    label="Download JSON",
                    data=df.to_json(orient="records"),
                    file_name=f"{selected_state}_libraries.json",
                    mime="application/json"
                )
        else:
            st.error("No data found for this state.")

# =============================================
# DEALSHEAVEN SCRAPER
# =============================================

def dealsheaven_app():
    st.title("🛍️ DealSphere Pro - Shopping Assistant")

    @st.cache_data(ttl=3600)
    def get_all_stores():
        try:
            url = "https://dealsheaven.in/stores"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            stores = []
            for a in soup.select("ul.store-listings li a"):
                store_name = a.text.strip()
                store_url = urljoin(url, a.get("href", "").strip())
                if store_name and store_url:
                    stores.append({"name": store_name, "url": store_url})
            return stores
        except Exception as e:
            st.error(f"Error fetching stores: {e}")
            return []

    def get_page_count(store_url, search_query=None):
        try:
            url = f"{store_url}?keyword={search_query}" if search_query else store_url
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            pagination = soup.find('ul', class_='pagination')
            if pagination:
                pages = [int(a.text) for a in pagination.find_all('a') if a.text.isdigit()]
                return max(pages) if pages else 1
            return 1
        except Exception as e:
            st.error(f"Error fetching page count: {e}")
            return 1

    def scrape_deals(store_info, max_pages, search_query=None):
        products = []
        store_url = store_info['url']
        store_name = store_info['name']
        
        for page in range(1, max_pages + 1):
            try:
                if page > 1:
                    time.sleep(1.5)
                
                base_url = f"{store_url}?page={page}"
                if search_query:
                    base_url += f"&keyword={search_query}"
                
                response = requests.get(base_url, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                product_cards = soup.find_all('div', class_='product-item-detail')
                
                if not product_cards:
                    continue

                for card in product_cards:
                    try:
                        if card.find('div', class_='ad-div'):
                            continue

                        product_name = card.find('h3').text.strip() if card.find('h3') else 'N/A'
                        img_tag = card.find('img', class_='lazy')
                        image_url = (img_tag.get('data-src') or img_tag.get('src')) if img_tag else 'N/A'
                        if image_url and image_url.startswith('//'):
                            image_url = f'https:{image_url}'
                        
                        link_tag = card.find('a', class_='btn')
                        shop_link = urljoin(store_url, link_tag['href']) if link_tag else 'N/A'
                        
                        products.append({
                            'Product Name': product_name,
                            'Image URL': image_url,
                            'Discount': card.find('div', class_='discount').text.strip() if card.find('div', class_='discount') else 'N/A',
                            'Original Price': card.find('p', class_='price').text.strip() if card.find('p', class_='price') else 'N/A',
                            'Current Price': card.find('p', class_='spacail-price').text.strip() if card.find('p', class_='spacail-price') else 'N/A',
                            'Store Name': store_name,
                            'Shop Now Link': shop_link
                        })
                    except Exception:
                        continue
            except Exception:
                continue
        return products

    # UI Components
    stores = get_all_stores()
    if not stores:
        st.error("Failed to load stores. Please try again later.")
        return
    
    selected_store = st.selectbox(
        "Select Store", 
        options=stores,
        format_func=lambda x: x['name'],
        index=0
    )
    
    if selected_store:
        search_query = st.text_input("🔍 Search products (optional)", key="search_input")
        
        with st.spinner("📡 Connecting to store..."):
            page_count = get_page_count(selected_store['url'], search_query)
        
        max_pages = st.selectbox(
            "Pages to scan",
            options=list(range(1, page_count + 1)),
            index=0,
            help="Number of pages to search through"
        )

        if st.button("🚀 Start Scraping", type="primary"):
            with st.spinner(f"🕵️ Scanning {selected_store['name']}..."):
                deals = scrape_deals(selected_store, max_pages, search_query)
            
            if deals:
                st.success(f"🎉 Found {len(deals)} deals!")
                st.dataframe(
                    pd.DataFrame(deals),
                    column_config={
                        "Image URL": st.column_config.ImageColumn(width="small"),
                        "Shop Now Link": st.column_config.LinkColumn()
                    },
                    use_container_width=True
                )
                
                # Export options
                st.markdown("---")
                st.subheader("📤 Export Results")
                cols = st.columns(3)
                with cols[0]:
                    st.download_button(
                        "📥 CSV",
                        data=pd.DataFrame(deals).to_csv(index=False).encode('utf-8'),
                        file_name=f"{selected_store['name']}_deals.csv",
                        mime="text/csv"
                    )
                with cols[1]:
                    excel_data = BytesIO()
                    pd.DataFrame(deals).to_excel(excel_data, index=False)
                    st.download_button(
                        "📊 Excel",
                        data=excel_data,
                        file_name=f"{selected_store['name']}_deals.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                with cols[2]:
                    st.download_button(
                        "📄 JSON",
                        data=json.dumps(deals, indent=2),
                        file_name=f"{selected_store['name']}_deals.json",
                        mime="application/json"
                    )
            else:
                st.warning("⚠️ No deals found. Try different search terms or pages!")

# =============================================
# MAIN APPLICATION
# =============================================

def main():
    st.sidebar.title("Navigation")
    scraper_choice = st.sidebar.selectbox(
        "Select Scraper",
        ["Public Libraries", "DealsHeaven Scraper"],
        index=0,
        help="Choose which scraping tool to use"
    )

    st.sidebar.markdown("---")
    st.sidebar.info("""
    **Web Scraper Pro**\n
    Professional scraping suite with:\n
    - Library Database Explorer\n
    - E-commerce Deal Finder\n
    - Multi-format Export Options
    """)

    if scraper_choice == "Public Libraries":
        public_libraries_app()
    elif scraper_choice == "DealsHeaven Scraper":
        dealsheaven_app()

if __name__ == "__main__":
    main()
#adding css