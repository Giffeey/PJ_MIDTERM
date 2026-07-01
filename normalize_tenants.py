"""
Normalize tenant names across all CSV files for consistent SNA.
Maps all variants to UPPERCASE canonical names with consistent spacing.
"""
import csv, glob, os, re

DATA_DIR = r"C:\DADS7201\PJ_MIDTERM\Data"

# Build normalization map from analysis output
# Canonical form = UPPERCASE with consistent single-space separation
NORMALIZE = {
    # ---- CRG brands (must match app.py CRG edge names) ----
    "MISTER DONUT": "MISTER DONUT",
    "KFC": "KFC",
    "AUNTIE ANNE'S": "AUNTIE ANNE'S",
    "PEPPER LUNCH": "PEPPER LUNCH",
    "KATSUYA": "KATSUYA",
    "YOSHINOYA": "YOSHINOYA",
    "OOTOYA": "OOTOYA",
    "COLD STONE": "COLD STONE",
    "SOMTAM NUA": "SOMTAM NUA",
    "CHABUTON": "CHABUTON",
    "SALAD FACTORY": "SALAD FACTORY",
    "SHINKANZEN SUSHI": "SHINKANZEN SUSHI",
    # ---- CRC brands ---- 
    "CENTRAL DEPARTMENT STORE": "CENTRAL DEPARTMENT STORE",
    "ROBINSON DEPARTMENT STORE": "ROBINSON DEPARTMENT STORE",
    "POWER BUY": "POWER BUY",
    "SUPER SPORTS": "SUPER SPORTS",  # also SUPERSORTS
    "BIG C": "BIG C",
    "TOPS": "TOPS",
    "TOPS FOOD HALL": "TOPS FOOD HALL",
    "TOPS DAILY": "TOPS DAILY",
    "B2S": "B2S",
    "OFFICEMATE": "OFFICEMATE",
    "MATSUKIYO": "MATSUKIYO",
    "THAIWATSU": "THAIWATSU",
    "BIG CAMERA": "BIG CAMERA",
    # ---- Common inconsistencies ----
    "COCO ICHIBANYA": "COCO ICHIBANYA",
    "LAEM CHAROEN SEAFOOD": "LAEM CHAROEN SEAFOOD",
    "CHARLES & KEITH": "CHARLES & KEITH",
    "BATH & BODY WORKS": "BATH & BODY WORKS",
    "TMB THANACHART BANK": "TMB THANACHART BANK",
    "SUPER RICH": "SUPER RICH",
    "SUPER RICH THAILAND": "SUPER RICH THAILAND",
    "POTATO CORNER": "POTATO CORNER",
    "STARBUCKS COFFEE": "STARBUCKS COFFEE",
    "SWENSEN'S": "SWENSEN'S",
    "MK RESTAURANTS": "MK RESTAURANTS",
    "FUJI JAPANESE RESTAURANT": "FUJI JAPANESE RESTAURANT",
    "MO-MO-PARADISE": "MO-MO-PARADISE",
    "THE PIZZA COMPANY": "THE PIZZA COMPANY",
    "THE NORTH FACE": "THE NORTH FACE",
    "PRANAKORN BOAT NOODLE": "PRANAKORN BOAT NOODLE",
    "SUKISHI KOREAN CHARCOAL GRILL": "SUKISHI KOREAN CHARCOAL GRILL",
    "ZEN JAPANESE RESTAURANT": "ZEN JAPANESE RESTAURANT",
    "HAI DI LAO": "HAI DI LAO",
    "INTHANIN COFFEE": "INTHANIN COFFEE",
    "BOOST JUICE BARS": "BOOST JUICE BARS",
    "KUB KAO KUB PLA": "KUB KAO KUB PLA",
    "NICE TWO MEAT U": "NICE TWO MEAT U",
    "GUSS DAMN GOOD": "GUSS DAMN GOOD",
    "GARRETT POPCORN SHOPS": "GARRETT POPCORN SHOPS",
    "HUA SENG HONG": "HUA SENG HONG",
    "BOON TONG KEE": "BOON TONG KEE",
    "YOGURT LAND": "YOGURT LAND",
    "YOU & I SUKI": "YOU & I SUKI",
    "DR. PONG": "DR. PONG",
    "MR. SHAKE": "MR. SHAKE",
    "MR. DIY": "MR. DIY",
    "SUSHI PLUS": "SUSHI PLUS",
    "HAIR D' CRAFT": "HAIR D' CRAFT",
    "MAISON BERGER PARIS": "MAISON BERGER PARIS",
    "V SQUARE CLINIC": "V SQUARE CLINIC",
    "WALL STREET ENGLISH": "WALL STREET ENGLISH",
    "YAMANA MUSIC SCHOOL": "YAMAHA MUSIC SCHOOL",
    "KPN MUSIC ACADEMY": "KPN MUSIC ACADEMY",
    "ORIENTAL PRINCESS": "ORIENTAL PRINCESS",
    "CHARLOTTE TILBURY": "CHARLOTTE TILBURY",
    "CATH KIDSTON": "CATH KIDSTON",
    "CC DOUBLE O": "CC DOUBLE O",
    "CPS CHAPS": "CPS CHAPS",
    "KT OPTIC": "KT OPTIC",
    "SLC CLINIC": "SLC CLINIC",
    "TO B 1 HAIR STATION": "TO B 1 HAIR STATION",
    "KEY & SHOES SERVICE": "KEY & SHOES SERVICE",
    "DR. TAT OFF & HAIR REMOVAL LASER CLINIC": "DR. TAT OFF & HAIR REMOVAL LASER CLINIC",
    "HANGTHONG WHANG TOH KANG YAOWARAJ": "HANGTHONG WHANG TOH KANG YAOWARAJ",
    "YOMIE'S RICE X YOGURT": "YOMIE'S RICE X YOGURT",
    "MATH TALENT BY DR. YING": "MATH TALENT BY DR. YING",
    "PULL & BEAR": "PULL & BEAR",
    "FIRE TIGER BY SEOULCIAL CLUB": "FIRE TIGER BY SEOULCIAL CLUB",
    "BB BEYOND D-BOX": "BB BEYOND D-BOX",
    "ISTUDIO BY COPPERWIRED": "ISTUDIO BY COPPERWIRED",
    "LEGO CERTIFIED STORE": "LEGO CERTIFIED STORE",
    "UOB EXPRESS": "UOB EXPRESS",
    "LEVI'S": "LEVI'S",
    "CHESTER'S": "CHESTER'S",
    "BEARD PAPA'S": "BEARD PAPA'S",
    "KIEHL'S": "KIEHL'S",
    "L'OCCITANE": "L'OCCITANE",
    "MARKS & SPENCER": "MARKS & SPENCER",
    "VICTORIA'S SECRET": "VICTORIA'S SECRET",
    "MC DONALD'S": "MC DONALD'S",
    "BEN'S COOKIES": "BEN'S COOKIES",
    "KRUNGSRI FIRST CHOICE": "KRUNGSRI FIRST CHOICE",
    "SF BRAND NAME": "SF BRAND NAME",
    "BIG MAC DIGITAL PRINTING": "BIG MAC DIGITAL PRINTING",
    "EYE LAB EXCLUSIVE": "EYE LAB EXCLUSIVE",
    "DR. SMOOTH LIFE": "DR. SMOOTH LIFE",
    "AES CLASS CLINIC": "AES CLASS CLINIC",
    "PIM @ POST": "PIM @ POST",
    "MASSAGE CHAIR NXN": "MASSAGE CHAIR NXN",
    "SANTA FE'": "SANTA FE'",
    "SANTA FE' STEAK": "SANTA FE' STEAK",
    "JING JAI MARKET": "JING JAI MARKET",
    "S. B. FURNITURE": "S. B. FURNITURE",
    "STYLE BALA SHOP": "STYLE BALA SHOP",
    "YALE SMART SHOP": "YALE SMART SHOP",
    "PINK SHARK CAR WASH": "PINK SHARK CAR WASH",
}

def canonical(name):
    """Convert ANY tenant name to its canonical form."""
    name = name.strip()
    # First check direct mapping
    if name in NORMALIZE:
        return NORMALIZE[name]
    # Check case-insensitive
    key = name.upper()
    if key in NORMALIZE:
        return NORMALIZE[key]
    # Try removing spaces (for fused words like COCOICHIBANYA)
    no_space = re.sub(r"\s+", "", name).upper()
    for canon in NORMALIZE.values():
        if re.sub(r"\s+", "", canon) == no_space:
            return canon
    # Try removing all non-alphanumeric
    clean = re.sub(r"[^A-Z0-9]", "", name.upper())
    for canon in NORMALIZE.values():
        if re.sub(r"[^A-Z0-9]", "", canon) == clean:
            return canon
    # Fallback: UPPERCASE
    return name.upper()

# ---- Verify normalization on all data ----
mall_files = glob.glob(os.path.join(DATA_DIR, "Central*.csv")) + [os.path.join(DATA_DIR, "MegaBangna.csv")]
stats = {"before": {}, "after": {}}
new_edges = []

for fpath in sorted(mall_files):
    with open(fpath, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()
    hdr_idx = 0
    for i, l in enumerate(lines):
        if l.strip().startswith("Source") and "Target" in l:
            hdr_idx = i
            break
    reader = csv.DictReader(lines[hdr_idx:])
    for row in reader:
        if None in row or row.get("Source") is None or row.get("Target") is None:
            continue
        raw = row["Source"].strip()
        canon = canonical(raw)
        stats["before"][raw] = stats["before"].get(raw, 0) + 1
        stats["after"][canon] = stats["after"].get(canon, 0) + 1

print(f"Before normalization: {len(stats['before'])} unique name variants")
print(f"After normalization:  {len(stats['after'])} unique canonical names")
print(f"Reduction: {len(stats['before']) - len(stats['after'])} variants eliminated")

# Print merged groups
from collections import defaultdict
reverse_map = defaultdict(set)
for raw in stats["before"]:
    canon = canonical(raw)
    reverse_map[canon].add(raw)

print("\n=== MERGED NAME GROUPS ===")
for canon, raws in sorted(reverse_map.items(), key=lambda x: -len(x[1])):
    if len(raws) > 1:
        print(f"{canon}:")
        for r in sorted(raws):
            print(f"  <- {r}")

# ---- Rewrite all CSV files ----
print("\n=== REWRITING FILES ===")
mall_files = glob.glob(os.path.join(DATA_DIR, "Central*.csv")) + [os.path.join(DATA_DIR, "MegaBangna.csv")]
for fpath in sorted(mall_files):
    with open(fpath, "r", encoding="utf-8-sig") as f:
        raw = f.read()
    lines = raw.splitlines()
    hdr_idx = 0
    for i, l in enumerate(lines):
        if l.strip().startswith("Source") and "Target" in l:
            hdr_idx = i
            break
    # Keep preamble as-is, rewrite CSV portion
    preamble = lines[:hdr_idx]
    csv_lines = lines[hdr_idx:]
    reader = csv.DictReader(csv_lines)
    out_rows = []
    for row in reader:
        if None in row or row.get("Source") is None or row.get("Target") is None:
            continue
        row["Source"] = canonical(row["Source"].strip())
        out_rows.append(row)

    with open(fpath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Source", "Target", "Weight", "Floor", "Category"])
        # Write preamble lines (if any)
        for line in preamble:
            f.write(line + "\n")
        writer.writeheader()
        for row in out_rows:
            writer.writerow(row)
    print(f"  Updated {os.path.basename(fpath)} ({len(out_rows)} rows)")

print("\nDone! All tenant names normalized.")
