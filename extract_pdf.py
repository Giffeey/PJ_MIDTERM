import fitz  # PyMuPDF
import os
import re

pdf_path = r"C:\DADS7201\PJ_MIDTERM\Data\cpn-or2025-en.pdf"
out_dir = r"C:\DADS7201\PJ_MIDTERM\Data\pdf_extracted"
os.makedirs(out_dir, exist_ok=True)

doc = fitz.open(pdf_path)
print(f"Total pages: {doc.page_count}")

# Keywords to search for key sections
section_keywords = [
    "Note 4", "Note 8", "Note 9", "subsidiaries", "joint venture", "related parties",
    "investment in subsidiary", "investment in associate", "investment in joint venture",
    "related party transaction", "group structure"
]

# First pass: find relevant pages by searching text
relevant_pages = set()
for i, page in enumerate(doc):
    text = page.get_text()
    text_lower = text.lower()
    for kw in section_keywords:
        if kw.lower() in text_lower:
            relevant_pages.add(i)
            break

print(f"\nFound {len(relevant_pages)} relevant pages: {sorted(relevant_pages)}")

# Extract text from relevant pages with context (include neighboring pages)
extract_pages = set()
for p in relevant_pages:
    for offset in range(-1, 3):  # 1 page before, 3 pages after for context
        np = p + offset
        if 0 <= np < doc.page_count:
            extract_pages.add(np)

extract_pages = sorted(extract_pages)
print(f"Extracting {len(extract_pages)} pages with context: {extract_pages}")

# Extract full text
all_text = []
for i in extract_pages:
    page = doc[i]
    text = page.get_text()
    all_text.append(f"\n{'='*80}\n=== PAGE {i+1} ===\n{'='*80}\n{text}")

full_text = "\n".join(all_text)
with open(os.path.join(out_dir, "relevant_sections.txt"), "w", encoding="utf-8") as f:
    f.write(full_text)
print(f"Saved relevant sections to relevant_sections.txt")

# Also extract table of contents pages (usually first ~5 pages)
toc_text = []
for i in range(min(10, doc.page_count)):
    page = doc[i]
    text = page.get_text()
    toc_text.append(f"\n=== PAGE {i+1} ===\n{text}")

with open(os.path.join(out_dir, "toc.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(toc_text))
print("Saved TOC pages")

# Extract every page's first 200 chars as page summary
page_summaries = []
for i, page in enumerate(doc):
    text = page.get_text()[:200].replace("\n", " ").strip()
    page_summaries.append(f"Page {i+1}: {text}")

with open(os.path.join(out_dir, "page_summaries.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(page_summaries))
print("Saved page summaries")

# Extract full document text (may be large, but useful for searching)
with open(os.path.join(out_dir, "full_text.txt"), "w", encoding="utf-8") as f:
    for i, page in enumerate(doc):
        text = page.get_text()
        f.write(f"\n=== PAGE {i+1} ===\n{text}")
print("Saved full text (all pages)")

doc.close()
print("\nDone!")
