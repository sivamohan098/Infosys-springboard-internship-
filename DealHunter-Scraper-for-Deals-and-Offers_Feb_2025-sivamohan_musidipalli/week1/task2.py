# -*- coding: utf-8 -*-
import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
from io import BytesIO
from urllib.parse import urljoin
import time

# Set page config
st.set_page_config(page_title="DealsSphere Pro", layout="wide", page_icon="🛍️")

# --------------------------
# FUNCTION DEFINITIONS
# --------------------------

@st.cache_data(ttl=3600)
def get_all_stores():
    """Fetch all stores from DealsHeaven 'Stores' page with caching."""
    url = "https://dealsheaven.in/stores"
    try:
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
    """Determine the number of pages for a given store."""
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
    """Scrape product details with flexible search."""
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
                st.write(f"Scanned page {page} - no products found")
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
                except Exception as card_error:
                    continue
                    
        except Exception as page_error:
            st.error(f"Error accessing page {page}: {str(page_error)}")
            continue
            
    return products

# --------------------------
# UI COMPONENTS
# --------------------------

st.markdown("""
<style>
    .main-container {
        background: transparent;  /* Removed white background */
        border-radius: 15px;
        padding: 2rem;
        box-shadow: none; /* Removed shadow if unnecessary */
        margin: 20px 0;
    }
    .stSelectbox > div > div {
        border-radius: 8px !important;
    }
</style>
""", unsafe_allow_html=True)


def main():
    st.title("🛍️ DealSphere Pro - Unified Shopping Platform")
    
    with st.container():
        st.markdown("<div class='main-container'>", unsafe_allow_html=True)
        
        # Store selection
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
            # Always visible search and page controls
            search_query = st.text_input("🔍 Search products (optional)", key="search_input")
            
            # Get page count (works with or without search query)
            with st.spinner("Checking store pages..."):
                page_count = get_page_count(selected_store['url'], search_query)
            
            # Always show page dropdown
            max_pages = st.selectbox(
                "Pages to scrape",
                options=list(range(1, page_count + 1)),
                index=0,
                help="Select number of pages to scan"
            )

            if st.button("🚀 Start Scraping", type="primary"):
                with st.spinner(f"Scraping {selected_store['name']}..."):
                    deals = scrape_deals(selected_store, max_pages, search_query)
                
                if deals:
                    st.success(f"Found {len(deals)} deals!")
                    st.dataframe(
                        pd.DataFrame(deals),
                        column_config={
                            "Image URL": st.column_config.ImageColumn(width="small"),
                            "Shop Now Link": st.column_config.LinkColumn()
                        },
                        use_container_width=True
                    )
                    
                    # Export options
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.download_button(
                            "📥 CSV",
                            data=pd.DataFrame(deals).to_csv(index=False).encode('utf-8'),
                            file_name=f"{selected_store['name']}_deals.csv",
                            mime="text/csv"
                        )
                    with col2:
                        excel_data = BytesIO()
                        pd.DataFrame(deals).to_excel(excel_data, index=False)
                        st.download_button(
                            "📊 Excel",
                            data=excel_data,
                            file_name=f"{selected_store['name']}_deals.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    with col3:
                        st.download_button(
                            "📄 JSON",
                            data=json.dumps(deals, indent=2),
                            file_name=f"{selected_store['name']}_deals.json",
                            mime="application/json"
                        )
                else:
                    st.warning("No deals found in scanned pages. Try different parameters!")
        
        st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
#