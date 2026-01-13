import requests
from bs4 import BeautifulSoup
import time
import os
import re

# --- CONFIGURATION ---
API_KEY = "XXXXXXX"
SEARCH_ENGINE_ID = "XXXXXXX"

# To get 500+ leads, we use multiple queries. 
# Google limits each query to 100 results. 10 queries = 1,000 potential results.
# --- UPDATE YOUR QUERIES LIST WITH THIS ---
# --- DYNAMIC QUERY GENERATOR ---
industries = [
    "Logistics", "Solar Energy", "SaaS", "Manufacturing", "HVAC", 
    "Marketing Agency", "Law Firm", "Recruitment", "Accounting", 
    "Real Estate", "Printing", "Wholesale", "Security Systems", 
    "Consulting", "Cleaning Services", "Landscaping", "Insurance"
]

locations = [
    "site:.com", "site:.us", "site:.co.uk", "site:.ie", 
    "site:.ca", "site:.com.au", "site:.eu", "site:.net"
]

intents = [
    '"request a callback"', 
    '"request callback"', 
    '"call me back"', 
    '"schedule a call"'
]

# Generate unique combinations
DYNAMIC_QUERIES = []
for industry in industries:
    for loc in locations:
        # Mixes industry + intent + location
        query = f'({intents[0]} OR {intents[1]}) "{industry}" {loc}'
        DYNAMIC_QUERIES.append(query)

# Shuffle them so every run feels 'fresh'
import random
random.shuffle(DYNAMIC_QUERIES)

# Limit to 50 queries per run to stay within API safety
QUERIES = DYNAMIC_QUERIES[:50] 
# ------------------------------

HISTORY_FILE = "scraped_history.txt"
FOUND_FILE = "global_leads.csv"

# --- FILE MANAGEMENT ---

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f)
    return set()

def load_existing_lead_urls():
    if not os.path.exists(FOUND_FILE):
        return set()
    urls = set()
    with open(FOUND_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
        if len(lines) > 1: # Skip header
            for line in lines[1:]:
                parts = line.split(',')
                if len(parts) > 1:
                    urls.add(parts[1].strip())
    return urls

def save_to_history(url):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(url + "\n")

def get_next_lead_number():
    if not os.path.exists(FOUND_FILE):
        return 1
    with open(FOUND_FILE, "r", encoding="utf-8") as f:
        return sum(1 for line in f) # Header is line 1, first lead is line 2

def save_lead(url, method):
    file_exists = os.path.exists(FOUND_FILE)
    lead_no = get_next_lead_number()
    with open(FOUND_FILE, "a", encoding="utf-8") as f:
        if not file_exists:
            f.write("No.,URL,Detection Method,Timestamp\n")
        f.write(f"{lead_no},{url.replace(',', '')},{method},{time.ctime()}\n")

# --- SEARCH & SCRAPE LOGIC ---

def get_search_results(query, api_key, cx, start_index=1):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {'q': query, 'key': api_key, 'cx': cx, 'num': 10, 'start': start_index}
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if "items" in data:
            return [item['link'] for item in data['items']]
        return []
    except Exception as e:
        print(f"\n[!] Search Error: {e}")
        return []

def has_phone_callback_form(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=12)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Broad Intent Keywords
        callback_pattern = re.compile(r'call[- ]?back|call me back|request call|callback', re.IGNORECASE)
        # 2. Specific Phone Field Keywords (Excluding pure WhatsApp)
        phone_keywords = r'phone|mobile|tel|mob|gsm|cell|contact[- ]?number|telephone|digits'
        phone_pattern = re.compile(phone_keywords, re.IGNORECASE)

        forms = soup.find_all('form')
        for form in forms:
            form_html = str(form).lower()
            form_text = form.get_text().lower()
            
            # Form must mention callback intent
            has_intent = callback_pattern.search(form_text) or callback_pattern.search(form_html)
            
            # Form must have a phone-related input
            has_phone_input = False
            # Check <input type="tel">
            if form.find_all('input', attrs={"type": "tel"}):
                has_phone_input = True
            
            # Check attributes (name, id, placeholder)
            if not has_phone_input:
                for input_tag in form.find_all(['input', 'textarea']):
                    attr_values = " ".join([str(val) for val in input_tag.attrs.values()]).lower()
                    if phone_pattern.search(attr_values):
                        has_phone_input = True
                        break
            
            if has_intent and has_phone_input:
                return True, "Phone Callback Form"

        return False, None
    except:
        return False, None

# --- MAIN RUNNER ---

if __name__ == "__main__":
    scraped_history = load_history()
    existing_leads = load_existing_lead_urls()
    
    print("--- [GLOBAL SCRAPER STARTING] ---")
    print(f"Loaded History: {len(scraped_history)} | Existing Leads: {len(existing_leads)}")

    for current_query in QUERIES:
        print(f"\n>> NEW SEARCH: {current_query}")
        
        # Range 0-10 fetches 10 pages (100 total links) per query
        for page in range(10): 
            start_node = (page * 10) + 1
            print(f"   Fetching results {start_node} to {start_node+9}...")
            
            links = get_search_results(current_query, API_KEY, SEARCH_ENGINE_ID, start_index=start_node)
            
            if not links:
                print("   No more results for this query.")
                break

            for link in links:
                # SKIP IF ALREADY IN HISTORY OR ALREADY A LEAD
                if link in scraped_history or link in existing_leads:
                    continue 
                
                print(f"   Analyzing: {link}", end="... ", flush=True)
                is_valid, method = has_phone_callback_form(link)
                
                if is_valid:
                    print("YES")
                    save_lead(link, method)
                    existing_leads.add(link)
                else:
                    print("NO")
                
                # Update history to avoid re-checking this URL ever again
                scraped_history.add(link)
                save_to_history(link)
                time.sleep(1.2) # Polite delay


    print(f"\n--- [FINISHED] Total Leads in CSV: {get_next_lead_number() - 1} ---")
