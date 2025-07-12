# Infosys-springboard-internship-

Web scraping has become a vital technique in automating data extraction from websites. This project, DealHunter Scraper for Deals and Offers, focuses on automating the extraction of deals and offers from e-commerce and public library websites using Python, Streamlit, Playwright, BeautifulSoup, and advanced AI models (OpenAI, Gemini, and Groq APIs). The scraper provides real-time data collection, filtering, and structured output, allowing users to make timely and informed decisions. This document details the design, implementation, challenges, and future enhancements of the system, along with its ethical and technical considerations

Project Statement
The primary goal of this project is to develop an automated scraper that extracts critical deal information—such as headers, titles, descriptions, prices, ratings, seller details, images, and links—from websites like DealsHeaven and PublicLibraries. By integrating AI summarization, the project not only collects raw data but also enhances it for better readability and decision support.

Expected Outcomes
•	Real-Time Data Extraction: Automated retrieval of deals and offers as they are posted.
•	Enhanced Data Accuracy: Minimization of manual errors through structured data processing.
•	Improved Usability: AI-powered summarization to present data in a user-friendly format.
•	Ethical Scraping: Adherence to best practices ensuring compliance with website policies.
•	User Empowerment: Enabling users to quickly identify the best deals for cost savings and improved satisfaction.
System Architecture
The DealHunter Scraper follows a modular architecture, comprising the following layers:
1. Web Scraping Layer
•	Tools: Playwright for dynamic content and BeautifulSoup for HTML parsing.
•	Function: Extracts raw HTML from targeted websites while handling JavaScript-rendered pages and AJAX calls.
•	Features: Headless browsing and user-agent rotation to mimic genuine browsing behavior.
2. Data Processing Layer
•	Function: Cleans and structures the raw HTML data.
•	Methods: Uses custom parsers to extract deal-specific details such as titles, prices, and images while managing variations in website layouts.
3. AI-Powered Processing Layer
•	Function: Enhances data usability through summarization and intelligent extraction.
•	APIs: Integration with OpenAI GPT, Google Gemini, and Groq AI to transform unstructured data into structured JSON.
4. Storage and Retrieval Layer
•	Formats: Saves data in CSV, JSON, and Excel formats.
•	Purpose: Ensures easy export and further analysis of scraped data.
5. User Interface Layer
•	Framework: Built with Streamlit for an intuitive, interactive UI.
•	Function: Allows users to enter URLs, set parameters, and view scraping results in real time.
<img width="1895" height="951" alt="Screenshot 2025-03-02 143150" src="https://github.com/user-attachments/assets/edd4db8e-dcde-42b3-bafe-9516401b9a76" />
<img width="1895" height="951" alt="Screenshot 2025-03-02 143150" src="https://github.com/user-attachments/assets/e08df64b-2513-45bf-8a16-8333a297635f" /><img width="1903" height="979" alt="Screenshot 2025-03-02 140143" src="https://github.com/user-attachments/assets/24abf67a-0fae-4bf2-adf7-b1914b29d545" />



