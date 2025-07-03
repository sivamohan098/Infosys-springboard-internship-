# chunk_processor.py
import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
import google.generativeai as genai
from tabulate import tabulate

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

SYSTEM_MESSAGE = "You are an assistant that summarizes markdown content."
USER_MESSAGE = "Summarize the following markdown content:"

def get_text_chunks(markdown_content):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    chunks = text_splitter.split_text(markdown_content)
    return chunks

def process_chunk(chunk):
    prompt = f"{SYSTEM_MESSAGE}\n{USER_MESSAGE}\n{chunk}"
    model_obj = genai.GenerativeModel(
        'gemini-2.0-flash',
        generation_config={"response_mime_type": "text/plain"}
    )
    completion = model_obj.generate_content(prompt)
    if getattr(completion, "finish_reason", None) == 4 or not hasattr(completion, "text"):
        return "Gemini model did not return text."
    return completion.text.strip()

def process_markdown(markdown_content):
    chunks = get_text_chunks(markdown_content)
    results = []
    for i, chunk in enumerate(chunks):
        response = process_chunk(chunk)
        results.append({"chunk": f"Chunk {i+1}", "response": response})
    return results

def display_results_table(results):
    table = tabulate(
        [(item["chunk"], item["response"]) for item in results],
        headers=["Chunk", "Gemini Response"],
        tablefmt="grid"
    )
    return table
