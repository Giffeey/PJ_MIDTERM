import re

# Read the extracted text  
with open(r'C:\DADS7201\PJ_MIDTERM\Data\pdf_extracted\full_text.txt', 'r', encoding='utf-8') as f:
    text = f.read()

# Find note sections by page markers
pages = text.split('=== PAGE ')

# First pass: map page numbers to content
page_map = {}
for p in pages:
    if '===' not in p:
        continue
    lines = p.split('\n', 1)
    try:
        page_num = int(lines[0].strip().rstrip(' ==='))
        content = lines[1] if len(lines) > 1 else ''
        page_map[page_num] = content
    except:
        continue

# Search for key terms across all pages
search_terms = [
    "Common Ground", "MeSpace", "Self Storage", "North Bangkok", "Synergistic Property",
    "SF Development", "Mega Bangna", "SF Development", "Dusit Thani", "Viman Suriya",
    "Porto Worldwide", "Central Village", "Mitsubishi Estate", "i-Berhad", "i-City",
    "Hongkong Land", "CPN and HKL", "Grand Canal Land", "Siam Future",
    "Phenomenon Creation", "CPN Global Vietnam", "Note 4", "Note 8", "Note 9"
]

print("=== SEARCH RESULTS ===")
for term in search_terms:
    count = 0
    for page_num in sorted(page_map.keys()):
        content = page_map[page_num]
        if term.lower() in content.lower():
            if count == 0:
                print(f"\n--- {term} ---")
            count += 1
            # Find context around the match
            idx = content.lower().find(term.lower())
            start = max(0, idx - 100)
            end = min(len(content), idx + 200)
            snippet = content[start:end].replace('\n', ' ').strip()
            print(f"  Page {page_num}: ...{snippet}...")

# Extract the Note 8 (associates and JVs) and Note 9 (subsidiaries) tables
print("\n\n=== FULL LIST OF SUBSIDIARIES (Note 9) ===")
note9_start = text.find("9 \nInvestments in subsidiaries")
if note9_start == -1:
    note9_start = text.find("9\nInvestments in subsidiaries")
if note9_start == -1:
    note9_start = text.find("Investments in subsidiaries and fund")

if note9_start >= 0:
    # Print from note 9 until page 432 (limits)
    note9_end = text.find("Non-controlling interests", note9_start)
    if note9_end == -1:
        note9_end = note9_start + 15000
    note9_text = text[note9_start:note9_end]
    print(note9_text[:8000])

print("\n\n=== FULL LIST OF ASSOCIATES AND JVS (Note 8) ===")
note8_start = text.find("8 \nInvestments in associates and joint ventures")
if note8_start == -1:
    note8_start = text.find("8\nInvestments in associates and joint ventures")
if note8_start == -1:
    note8_start = text.find("Investments in associates")

if note8_start >= 0:
    note8_end = text.find("Material associates", note8_start)
    if note8_end == -1:
        note8_end = note8_start + 15000
    note8_text = text[note8_start:note8_end]
    print(note8_text[:8000])

# Extract the shareholding structure section (pages ~31-52)
print("\n\n=== SHAREHOLDING STRUCTURE ===")
for pn in range(30, 55):
    if pn in page_map:
        content = page_map[pn]
        if any(w in content.lower() for w in ['subsidiar', 'shareholding', 'group structure', 'organization']):
            print(f"\n--- Page {pn} ---")
            print(content[:1000])

print("\n\n=== RELATED PARTY TRANSACTIONS (Section 9.2) ===")
for pn in range(335, 380):
    if pn in page_map:
        content = page_map[pn]
        if any(w in content.lower() for w in ['related party', 'subsidiar', 'joint venture', 'associate']):
            print(f"\n--- Page {pn} ---")
            print(content[:1500])

print("\n\n=== NOTE 4 SUBSIDIARIES LIST ===")
for pn in range(393, 418):
    if pn in page_map:
        content = page_map[pn]
        if '4' in content[:50] or 'subsidiary' in content.lower()[:500]:
            print(f"\n--- Page {pn} ---")
            print(content[:2000])
