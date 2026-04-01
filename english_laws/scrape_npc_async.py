#!/usr/bin/env python3
"""
Scrape English laws from NPC website - async version
"""

import asyncio
import aiohttp
import os
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "http://www.npc.gov.cn/englishnpc/lawsoftheprc/"
OUTPUT_DIR = "."

def get_law_list_sync():
    """Get law list from NPC page with requests"""
    import requests
    url = BASE_URL + "index.html"
    response = requests.get(url, timeout=30)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")
    
    laws = []
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

async def scrape_law(session, law):
    """Scrape a single law"""
    print(f"Scraping: {law['title']}")
    
    if law["is_pdf"]:
        try:
            async with session.get(law["url"], timeout=60) as response:
                content = await response.read()
                filename = law["url"].split("/")[-1]
                pdf_path = os.path.join(OUTPUT_DIR, filename)
                with open(pdf_path, "wb") as f:
                    f.write(content)
                print(f"  ✓ PDF: {filename}")
                return {
                    "title": law["title"],
                    "url": law["url"],
                    "type": "pdf",
                    "filename": filename
                }
        except Exception as e:
            print(f"  ✗ Error downloading PDF: {e}")
            return None
    
    try:
        async with session.get(law["url"], timeout=30) as response:
            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")
            
            content = []
            for p in soup.find_all("p"):
                text = p.get_text(strip=True)
                if text and len(text) > 0:
                    content.append(text)
            
            if not content:
                # Try another selector
                for div in soup.find_all("div"):
                    text = div.get_text(strip=True)
                    if len(text) > 50:
                        content.append(text)
            
            full_text = "\n\n".join(content)
            
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
            
            print(f"  ✓ Saved: {json_filename}, {len(content)} paragraphs")
            return {
                "title": law["title"],
                "url": law["url"],
                "type": "html",
                "filename": json_filename,
                "paragraph_count": len(content)
            }
        
    except Exception as e:
        print(f"  ✗ Error scraping: {e}")
        return None

async def main():
    laws = get_law_list_sync()
    print(f"Found {len(laws)} laws total")
    
    conn = aiohttp.TCPConnector(limit=5)
    async with aiohttp.ClientSession(connector=conn) as session:
        tasks = [scrape_law(session, law) for law in laws]
        results = await asyncio.gather(*tasks)
    
    successful = [r for r in results if r is not None]
    
    with open(os.path.join(OUTPUT_DIR, "index.json"), "w", encoding="utf-8") as f:
        json.dump({
            "source": "National People's Congress of China (official English translation)",
            "total": len(successful),
            "laws": successful
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\nDone! Scraped {len(successful)}/{len(laws)} laws successfully")

if __name__ == "__main__":
    asyncio.run(main())
