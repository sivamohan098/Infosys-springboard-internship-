# scraper.py

import sys
import asyncio
# Set event loop policy for Windows
if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import os
import random
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
from playwright.async_api import async_playwright

from openai import OpenAI
import google.generativeai as genai
from groq import Groq

from assets import (
    USER_AGENTS, PRICING, HEADLESS_OPTIONS,
    SYSTEM_MESSAGE, USER_MESSAGE,
    LLAMA_MODEL_FULLNAME, GROQ_LLAMA_MODEL_FULLNAME
)

load_dotenv()

BASE_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = BASE_DIR / "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# -------------------------------------------------------------------
# Helper: Build a strict JSON schema for Gemini from user-selected fields
# -------------------------------------------------------------------
def create_dynamic_schema(field_names: List[str]) -> dict:
    """
    Build a strict JSON schema for Gemini based on the user-selected fields.
    All fields are required and must be strings.
    """
    schema_properties = {}
    for field in field_names:
        schema_properties[field] = {"type": "string"}

    strict_schema = {
        "type": "object",
        "properties": {
            "listings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": schema_properties,
                    "required": list(field_names)  # Must have all user-selected fields
                }
            }
        },
        "required": ["listings"]
    }
    return strict_schema


# -------------------------------------------------------------------
# Helper: Ensure each listing has all user-selected fields (fill missing with "")
# -------------------------------------------------------------------
def postprocess_listings(listings, field_names: List[str]):
    """
    Ensure each listing has all field_names, fill missing with empty string.
    """
    for item in listings:
        for field in field_names:
            if field not in item:
                item[field] = ""
    return listings


async def fetch_html_playwright(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=random.choice(USER_AGENTS))
        page = await context.new_page()
        await page.goto(url, timeout=60000)

        # Multiple scroll attempts to load dynamic content
        for _ in range(5):
            await page.evaluate("window.scrollBy(0, document.body.scrollHeight);")
            await asyncio.sleep(2)  # adjust as needed

        html = await page.content()

        # Debug save
        debug_path = OUTPUT_DIR / "debug.html"
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(html)

        await browser.close()
        return html


def clean_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    for element in soup.find_all(['header', 'footer']):
        element.decompose()
    return str(soup)


def html_to_markdown_with_readability(html_content):
    cleaned_html = clean_html(html_content)
    converter = html2text.HTML2Text()
    converter.ignore_links = False
    return converter.handle(cleaned_html)


def save_raw_data(raw_data, timestamp, output_folder='output'):
    os.makedirs(output_folder, exist_ok=True)
    path = os.path.join(output_folder, f'rawData_{timestamp}.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(raw_data)
    return path


def create_dynamic_listing_model(field_names: List[str]) -> Type[BaseModel]:
    """
    Dynamically build a Pydantic model based on the user-selected fields.
    All fields must be strings.
    """
    fields = {field: (str, ...) for field in field_names}
    return create_model('DynamicListingModel', **fields)


def create_listings_container_model(listing_model: Type[BaseModel]) -> Type[BaseModel]:
    """
    Container model that holds a list of the listing model.
    """
    return create_model('DynamicListingsContainer', listings=(List[listing_model], ...))


def fix_json_output(broken_json: str, model_obj, system_message: str, user_message: str, data: str) -> str:
    fix_prompt = (
        "\nThe JSON above is invalid or incomplete. "
        "Please correct it and output only valid JSON with no additional text."
    )
    full_prompt = (
        system_message
        + "\n" + user_message + data
        + fix_prompt
        + "\nBroken JSON:\n" + broken_json
    )
    fixed_completion = model_obj.generate_content(full_prompt)
    return fixed_completion.text


def format_data(data, DynamicListingsContainer, DynamicListingModel, selected_model):
    """
    Pass the chunk 'data' to the selected model, parse JSON, post-process, and return.
    """
    token_counts = {}
    field_list = list(DynamicListingModel.__fields__.keys())

    # -----------------------------------
    # 1. GPT-based (OpenAI) Models
    # -----------------------------------
    if selected_model in ["gpt-4o-mini", "gpt-4o-2024-08-06"]:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        completion = client.beta.chat.completions.parse(
            model=selected_model,
            messages=[
                {"role": "system", "content": SYSTEM_MESSAGE},
                {"role": "user", "content": USER_MESSAGE + data}
            ],
            response_format=DynamicListingsContainer
        )
        encoder = tiktoken.encoding_for_model(selected_model)
        input_token_count = len(encoder.encode(USER_MESSAGE + data))
        output_token_count = len(
            encoder.encode(json.dumps(completion.choices[0].message.parsed.dict()))
        )
        token_counts = {
            "input_tokens": input_token_count,
            "output_tokens": output_token_count
        }

        final_json = completion.choices[0].message.parsed.dict()
        # Post-process to ensure all fields exist
        if "listings" in final_json:
            final_json["listings"] = postprocess_listings(final_json["listings"], field_list)
        else:
            final_json["listings"] = []
        return final_json, token_counts

    # -----------------------------------
    # 2. Gemini (Google) Model
    # -----------------------------------
    elif selected_model == "gemini-2.0-flash":
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

        # Build a strict schema based on user-selected fields
        strict_schema = create_dynamic_schema(field_list)

        model_obj = genai.GenerativeModel(
            'gemini-2.0-flash',
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": strict_schema
            }
        )
        prompt = SYSTEM_MESSAGE + "\n" + USER_MESSAGE + data
        input_tokens = model_obj.count_tokens(prompt)
        completion = model_obj.generate_content(prompt)
        usage_metadata = completion.usage_metadata
        token_counts = {
            "input_tokens": usage_metadata.prompt_token_count,
            "output_tokens": usage_metadata.candidates_token_count
        }

        if getattr(completion, "finish_reason", None) == 4 or not hasattr(completion, "text"):
            print("Gemini model did not return text or was restricted.")
            final_json = {"listings": []}
        else:
            output_text = completion.text
            final_json = None
            try:
                final_json = json.loads(output_text)
            except json.JSONDecodeError as e:
                print("Initial JSON parsing failed:", e)
                # Attempt fix
                fixed_output = fix_json_output(
                    output_text, model_obj, SYSTEM_MESSAGE, USER_MESSAGE, data
                )
                try:
                    final_json = json.loads(fixed_output)
                    output_text = fixed_output
                except json.JSONDecodeError as e2:
                    print("Still invalid JSON after fix:", e2)

            if final_json is None:
                final_json = {"listings": []}

        # Post-process to ensure all fields exist
        if "listings" in final_json:
            final_json["listings"] = postprocess_listings(final_json["listings"], field_list)
        else:
            final_json["listings"] = []
        return final_json, token_counts

    # -----------------------------------
    # 3. Local Llama
    # -----------------------------------
    elif selected_model == "Llama3.1 8B":
        client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
        completion = client.chat.completions.create(
            model=LLAMA_MODEL_FULLNAME,
            messages=[
                {"role": "system", "content": SYSTEM_MESSAGE},
                {"role": "user", "content": USER_MESSAGE + data}
            ],
            temperature=0.7,
        )
        response_content = completion.choices[0].message.content
        parsed_response = json.loads(response_content)
        token_counts = {
            "input_tokens": completion.usage.prompt_tokens,
            "output_tokens": completion.usage.completion_tokens
        }

        if "listings" in parsed_response:
            parsed_response["listings"] = postprocess_listings(parsed_response["listings"], field_list)
        else:
            parsed_response["listings"] = []
        return parsed_response, token_counts

    # -----------------------------------
    # 4. Groq Model
    # -----------------------------------
    elif selected_model == "Groq Llama3.1 70b":
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_MESSAGE},
                {"role": "user", "content": USER_MESSAGE + data}
            ],
            model=GROQ_LLAMA_MODEL_FULLNAME,
        )
        response_content = completion.choices[0].message.content
        parsed_response = json.loads(response_content)
        token_counts = {
            "input_tokens": completion.usage.prompt_tokens,
            "output_tokens": completion.usage.completion_tokens
        }

        if "listings" in parsed_response:
            parsed_response["listings"] = postprocess_listings(parsed_response["listings"], field_list)
        else:
            parsed_response["listings"] = []
        return parsed_response, token_counts

    else:
        raise ValueError(f"Unsupported model: {selected_model}")


def save_formatted_data(formatted_data, timestamp, output_folder='output'):
    os.makedirs(output_folder, exist_ok=True)

    json_path = os.path.join(output_folder, f'sorted_data_{timestamp}.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(formatted_data, f, indent=4)

    try:
        if "listings" in formatted_data:
            df = pd.DataFrame(formatted_data["listings"])
        else:
            df = pd.DataFrame({"raw_data": [formatted_data]})
    except Exception as e:
        print("Error creating DataFrame from JSON. Using fallback. Error:", e)
        df = pd.DataFrame({"raw_data": [formatted_data]})

    excel_path = os.path.join(output_folder, f'sorted_data_{timestamp}.xlsx')
    df.to_excel(excel_path, index=False)
    return df


def calculate_price(token_counts, model):
    input_token_count = token_counts.get("input_tokens", 0)
    output_token_count = token_counts.get("output_tokens", 0)
    input_cost = input_token_count * PRICING[model]["input"]
    output_cost = output_token_count * PRICING[model]["output"]
    total_cost = input_cost + output_cost
    return input_token_count, output_token_count, total_cost


if __name__ == "__main__":
    # Example usage (unchanged from previous):
    url = "https://publiclibraries.com/state/alabama/"
    fields = ["city", "library", "address", "zip", "phone"]  # example
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    raw_html = asyncio.run(fetch_html_playwright(url))
    markdown = html_to_markdown_with_readability(raw_html)
    save_raw_data(markdown, timestamp)

    # Create dynamic models from user fields
    DynamicListingModel = create_dynamic_listing_model(fields)
    DynamicListingsContainer = create_listings_container_model(DynamicListingModel)

    selected_model = "gemini-2.0-flash"
    formatted_data, token_counts = format_data(
        markdown,
        DynamicListingsContainer,
        DynamicListingModel,
        selected_model
    )

    df = save_formatted_data(formatted_data, timestamp)
    print("Done. Check the 'output' folder for results.")
