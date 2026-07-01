with open(r'C:\DADS7201\PJ_MIDTERM\Data\pdf_extracted\relevant_sections.txt', 'r', encoding='utf-8') as f:
    text = f.read()

print(f'File size: {len(text)} chars')
print(f'Number of lines: {text.count(chr(10))}')

for term in ['subsidiar', 'joint venture', 'related party', 'investment in', 'Note', 'NOTE', 'Notes']:
    count = text.lower().count(term.lower())
    print(f'Count of "{term}": {count}')

# Show first 5000 chars
print("\n=== FIRST 5000 CHARS ===")
print(text[:5000])

# Search for any page with substantial content about groups
lines = text.split('\n')
for i, line in enumerate(lines):
    low = line.lower()
    if any(w in low for w in ['subsidiar', 'joint venture', 'investee', 'shareholding', 'structure']):
        ctx_start = max(0, i-2)
        ctx_end = min(len(lines), i+3)
        for j in range(ctx_start, ctx_end):
            print(f"  L{j}: {lines[j][:200]}")
        print("  ---")
