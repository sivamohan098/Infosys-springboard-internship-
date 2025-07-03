import os
import random
import time
import json
from datetime import datetime
from typing import List, Type
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from pydantic import BaseModel, create_model
import html2text
import tiktoken

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import demjson3  # Tolerant JSON parser fallback

load_dotenv()

###############################################################################
# Configuration
###############################################################################
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"
]
HEADLESS_OPTIONS = ["--headless=new", "--disable-gpu", "--disable-dev-shm-usage"]

# You can add more models and their pricing here if desired
PRICING = {
    "openai-gpt-3.5": {"input": 0.001, "output": 0.001},  # Example cost
    "gemini-2.0-flash": {"input": 0.0001, "output": 0.0003},
    "groq-llama": {"input": 0.0, "output": 0.0},          # Example
}

# Path to your local ChromeDriver
DRIVER_PATH = r"C:\Users\sivam\.wdm\drivers\chromedriver\win64\133.0.6943.126\chromedriver-win32\chromedriver.exe"
DRIVER_DIR = Path(__file__).parent / "drivers"
os.environ['WDM_LOCAL'] = str(DRIVER_DIR)

###############################################################################
# Selenium
###############################################################################
def setup_selenium():
    """Set up the Selenium driver with random user-agent & headless options."""
    options = Options()
    user_agent = random.choice(USER_AGENTS)
    options.add_argument(f"user-agent={user_agent}")
    for opt in HEADLESS_OPTIONS:
        options.add_argument(opt)

    service = Service(DRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def fetch_html_selenium(url: str) -> str:
    """Fetch page HTML using Selenium (with a small wait and scroll)."""
    driver = setup_selenium()
    try:
        driver.get(url)
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        return driver.page_source
    finally:
        driver.quit()

###############################################################################
# Convert HTML -> Markdown
###############################################################################
def clean_html(html_content: str) -> str:
    """Optionally remove header/footer if not needed."""
    soup = BeautifulSoup(html_content, 'html.parser')
    for elem in soup.find_all(['header', 'footer']):
        elem.decompose()
    return str(soup)

def html_to_markdown_with_readability(html_content: str) -> str:
    cleaned = clean_html(html_content)
    converter = html2text.HTML2Text()
    converter.ignore_links = False
    return converter.handle(cleaned)

def save_raw_data(raw_data: str, timestamp: str, output_folder='output'):
    """Save raw markdown data for debugging."""
    os.makedirs(output_folder, exist_ok=True)
    file_path = os.path.join(output_folder, f'rawData_{timestamp}.md')
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(raw_data)
    print(f"Raw data saved to {file_path}")
    return file_path

###############################################################################
# Dynamic Pydantic Models
###############################################################################
def create_dynamic_listing_model(fields: List[str]) -> Type[BaseModel]:
    field_defs = {field: (str, ...) for field in fields}
    return create_model("DynamicListingModel", **field_defs)

def create_listings_container_model(listing_model: Type[BaseModel]) -> Type[BaseModel]:
    return create_model("DynamicListingsContainer", listings=(List[listing_model], ...))

###############################################################################
# Building a System/User Prompt from your fields
###############################################################################
def build_prompts(fields: List[str]):
    # Create an example JSON snippet with all fields
    # e.g. {"deal name":"","price":""}
    fields_example = ", ".join([f'"{f}":""' for f in fields])

    system_message = f"""You are an intelligent text extraction assistant.
Return only valid JSON with no markdown or extra text.
Structure: {{"listings":[{{{fields_example}}}]}}
"""

    # user message listing the fields
    fields_str = ", ".join(fields)
    user_message = f"""
Extract the following fields from the text: {fields_str}
Return them in the JSON structure above. 
"""

    return system_message, user_message

###############################################################################
# Chunking the text to avoid truncation
###############################################################################
def chunk_text_by_tokens(text: str, model_name: str = "gpt-3.5-turbo", max_chunk_tokens=2500):
    """
    Splits a large string into smaller chunks by token count 
    so we don't exceed model output limits.
    We use GPT-3.5's tiktoken for approximate counting, 
    but it should be okay for other LLMs too.
    """
    encoder = tiktoken.encoding_for_model(model_name)
    tokens = encoder.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = start + max_chunk_tokens
        chunk_tokens = tokens[start:end]
        chunk_text = encoder.decode(chunk_tokens)
        chunks.append(chunk_text)
        start = end
    return chunks

###############################################################################
# Extract JSON from text
###############################################################################
def extract_json(text: str) -> dict:
    """Try standard json.loads, else fallback to demjson3."""
    text = text.strip("`").strip()
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        json_str = text[start:end]
        return json.loads(json_str)
    except Exception:
        try:
            return demjson3.decode(text)
        except Exception:
            return {"listings": [], "raw_text": text}

###############################################################################
# Main LLM format function
###############################################################################
def format_data(
    data: str,
    ContainerModel: Type[BaseModel],
    ListingModel: Type[BaseModel],
    selected_model: str,
    fields: List[str]
):
    """
    We handle multiple model choices here:
    - openai-gpt-3.5
    - gemini-2.0-flash
    - groq-llama
    etc.
    """
    system_message, user_message = build_prompts(fields)

    # If user picks openai-gpt-3.5
    if selected_model == "openai-gpt-3.5":
        import openai
        openai.api_key = os.getenv("OPENAI_API_KEY")
        # We'll do chunking with openai completions
        return _format_with_openai(data, system_message, user_message)

    elif selected_model == "gemini-2.0-flash":
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        return _format_with_gemini(data, system_message, user_message)

    elif selected_model == "groq-llama":
        import groq
        # We'll do chunking with groq's LLM (hypothetical)
        # Make sure you have your GROQ_API_KEY in .env
        return _format_with_groq(data, system_message, user_message)

    else:
        # If user picks something else, or not implemented, return empty
        print(f"WARNING: Model {selected_model} not implemented. Returning empty.")
        return "", {"input_tokens": 0, "output_tokens": 0}

###############################################################################
# Model-specific chunking for OpenAI
###############################################################################
def _format_with_openai(data, system_message, user_message):
    import openai

    # We'll chunk the data to avoid truncation
    text_chunks = chunk_text_by_tokens(data, max_chunk_tokens=2000)  # smaller chunk for openai
    all_listings = []
    total_input_tokens = 0
    total_output_tokens = 0

    for i, chunk in enumerate(text_chunks, start=1):
        prompt = f"{system_message}\n{user_message}\n{chunk}"

        # We'll use ChatCompletion. We can approximate tokens from usage.
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message + "\n" + chunk},
            ],
            temperature=0
        )
        usage = response["usage"]
        prompt_tokens = usage["prompt_tokens"]
        completion_tokens = usage["completion_tokens"]

        total_input_tokens += prompt_tokens
        total_output_tokens += completion_tokens

        response_text = response["choices"][0]["message"]["content"]
        parsed_chunk = extract_json(response_text)
        if "listings" in parsed_chunk:
            all_listings.extend(parsed_chunk["listings"])

    final_json = {"listings": all_listings}
    final_json_str = json.dumps(final_json, indent=4)

    token_counts = {
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens
    }
    return final_json_str, token_counts

###############################################################################
# Model-specific chunking for Gemini
###############################################################################
def _format_with_gemini(data, system_message, user_message):
    import google.generativeai as genai
    model_obj = genai.GenerativeModel('gemini-2.0-flash')

    text_chunks = chunk_text_by_tokens(data, max_chunk_tokens=2500)
    all_listings = []
    total_input_tokens = 0
    total_output_tokens = 0

    for i, chunk in enumerate(text_chunks, start=1):
        prompt = f"{system_message}\n{user_message}\n{chunk}"
        completion = model_obj.generate_content(prompt)
        usage = completion.usage_metadata

        prompt_token_count = getattr(usage, "prompt_token_count", 0)
        candidates_token_count = getattr(usage, "candidates_token_count", 0)
        total_input_tokens += prompt_token_count
        total_output_tokens += candidates_token_count

        response_text = completion.text.strip()
        parsed_chunk = extract_json(response_text)
        if "listings" in parsed_chunk:
            all_listings.extend(parsed_chunk["listings"])

    final_json = {"listings": all_listings}
    final_json_str = json.dumps(final_json, indent=4)

    token_counts = {
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens
    }
    return final_json_str, token_counts

###############################################################################
# Model-specific chunking for Groq
###############################################################################
def _format_with_groq(data, system_message, user_message):
    # Hypothetical example: if Groq has a Python library for LLM calls
    import groq

    text_chunks = chunk_text_by_tokens(data, max_chunk_tokens=2500)
    all_listings = []
    total_input_tokens = 0
    total_output_tokens = 0

    for i, chunk in enumerate(text_chunks, start=1):
        prompt = f"{system_message}\n{user_message}\n{chunk}"

        # Hypothetical usage
        completion = groq.generate(prompt, model="groq-llama-70b")
        # If groq returns usage in some manner
        total_input_tokens += completion["prompt_tokens"]
        total_output_tokens += completion["completion_tokens"]

        response_text = completion["text"].strip()
        parsed_chunk = extract_json(response_text)
        if "listings" in parsed_chunk:
            all_listings.extend(parsed_chunk["listings"])

    final_json = {"listings": all_listings}
    final_json_str = json.dumps(final_json, indent=4)

    token_counts = {
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens
    }
    return final_json_str, token_counts

###############################################################################
# Saving final data
###############################################################################
def save_formatted_data(formatted_data, timestamp, output_folder='output'):
    os.makedirs(output_folder, exist_ok=True)

    if isinstance(formatted_data, str):
        try:
            formatted_data_dict = json.loads(formatted_data)
        except json.JSONDecodeError:
            print("Warning: The provided formatted data is invalid JSON. Returning empty.")
            formatted_data_dict = {"listings": []}
    else:
        if hasattr(formatted_data, 'dict'):
            formatted_data_dict = formatted_data.dict()
        else:
            formatted_data_dict = formatted_data

    json_path = os.path.join(output_folder, f'sorted_data_{timestamp}.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(formatted_data_dict, f, indent=4)
    print(f"Formatted data saved to JSON at {json_path}")

    if isinstance(formatted_data_dict, dict):
        data_for_df = formatted_data_dict.get("listings", [])
    else:
        data_for_df = formatted_data_dict

    try:
        df = pd.DataFrame(data_for_df)
        print("DataFrame created successfully.")
        excel_path = os.path.join(output_folder, f'sorted_data_{timestamp}.xlsx')
        df.to_excel(excel_path, index=False)
        print(f"Formatted data saved to Excel at {excel_path}")
        return df
    except Exception as e:
        print(f"Error creating DataFrame or saving Excel: {e}")
        return None

def calculate_price(token_counts, model):
    input_tokens = token_counts.get("input_tokens", 0)
    output_tokens = token_counts.get("output_tokens", 0)
    if model not in PRICING:
        return input_tokens, output_tokens, 0.0
    cost_in = input_tokens * PRICING[model]["input"]
    cost_out = output_tokens * PRICING[model]["output"]
    total = cost_in + cost_out
    return input_tokens, output_tokens, total
