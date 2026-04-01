#!/usr/bin/env python3
"""
Scrape English laws from NPC website
"""

import requests
import os
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "http://www.npc.gov.cn/englishnpc/lawsoftheprc/"
OUTPUT_DIR = "."

def get_law_list():
    """Parse law list from NPC page"""
    url = BASE_URL + "index.html"
    response = requests.get(url)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")
    
    laws = []
    # The page is just a list of links, extract all
    for link in soup.find_all("a"):
        href = link.get("href")
        if not href or href.startswith("#") or href == "index.html":
            continue
        title = link.get_text(strip=True)
        if not title:
            continue
        full_url = urljoin(BASE_URL, href)
        laws.append({
            "title": title,
            "url": full_url,
            "is_pdf": href.endswith(".pdf")
        })
    
    return laws

def scrape_law(law):
    """Scrape a single law page"""
    print(f"Scraping: {law['title']} -> {law['url']}")
    
    if law["is_pdf"]:
        # PDF, download it directly
        try:
            response = requests.get(law["url"])
            filename = law["url"].split("/")[-1]
            pdf_path = os.path.join(OUTPUT_DIR, filename)
            with open(pdf_path, "wb") as f:
                f.write(response.content)
            print(f"  Downloaded PDF: {filename}")
            return {
                "title": law["title"],
                "url": law["url"],
                "type": "pdf",
                "filename": filename
            }
        except Exception as e:
            print(f"  Error downloading PDF: {e}")
            return None
    
    # HTML page
    try:
        response = requests.get(law["url"])
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extract content
        content = []
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if text and len(text) > 0:
                content.append(text)
        
        full_text = "\n\n".join(content)
        
        # Save JSON
        safe_title = "".join([c if c.isalnum() or c in " -_()" else "_" for c in law["title"]])
        json_filename = f"{safe_title}.json"
        output_path = os.path.join(OUTPUT_DIR, json_filename)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "title": law["title"],
                "url": law["url"],
                "content": full_text,
                "paragraphs": content
            }, f, ensure_ascii=False, indent=2)
        
        print(f"  Saved: {json_filename}, {len(content)} paragraphs")
        return {
            "title": law["title"],
            "url": law["url"],
            "type": "html",
            "filename": json_filename,
            "paragraph_count": len(content)
        }
        
    except Exception as e:
        print(f"  Error scraping: {e}")
        return None

def main():
    laws = get_law_list()
    print(f"Found {len(laws)} laws")
    
    results = []
    for law in laws:
        result = scrape_law(law)
        if result:
            results.append(result)
    
    # Save index
    with open(os.path.join(OUTPUT_DIR, "index.json"), "w", encoding="utf-8") as f:
        json.dump({
            "source": "National People's Congress of China (official English translation)",
            "total": len(results),
            "laws": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\nDone! Scraped {len(results)} laws successfully")

if __name__ == "__main__":
    main()
