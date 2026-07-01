"""
Normalize tenant names across all CSV files for consistent SNA.
Maps all variants to UPPERCASE canonical names with consistent spacing.
Also normalizes Category field (e.g. different spellings of main categories).
"""
import csv, glob, os, re
from collections import defaultdict

DATA_DIR = r"C:\DADS7201\PJ_MIDTERM\Data"

# ─── CANONICAL NAME MAP : variant → canonical ──────────────────────────
NORM = {

    # === PUNCTUATION / HYPHEN / APOSTROPHE VARIANTS ===
    "BAR B Q PLAZA": "BAR-B-Q PLAZA",
    "BAR-B-Q PLAZA": "BAR-B-Q PLAZA",
    "BATH AND BODY WORKS": "BATH & BODY WORKS",
    "BATH & BODY WORKS": "BATH & BODY WORKS",
    "BATH&BODY WORK": "BATH & BODY WORKS",
    "BB.TOYS": "BB TOYS",
    "BB TOYS": "BB TOYS",
    "BROWN CAFE": "BROWN CAFE",
    "BROWN CAFE'": "BROWN CAFE",
    "CAFE AMAZON": "CAFE AMAZON",
    "CAFE' AMAZON": "CAFE AMAZON",
    "CAFÉ AMAZON": "CAFE AMAZON",
    "G SHOCK": "G-SHOCK",
    "G-SHOCK": "G-SHOCK",
    "HAAGEN DAZS": "HAAGEN-DAZS",
    "HAAGEN-DAZS": "HAAGEN-DAZS",
    "JONES SALAD": "JONES SALAD",
    "JONES' SALAD": "JONES SALAD",
    "K. ACCESSORIES": "K. ACCESSORIES",
    "K.ACCESSORIES": "K. ACCESSORIES",
    "KOI THE": "KOI THE",
    "KOI THE'": "KOI THE",
    "LAO YUAN": "LAO YUAN",
    "LAO-YUAN": "LAO YUAN",
    "M LIFE": "M LIFE",
    "M.LIFE": "M LIFE",
    ".LIFE": "M LIFE",
    "MILK KIDS SALON & NAILS": "MILK KIDS SALON & NAILS",
    "MILK KIDS' SALON&NAILS": "MILK KIDS SALON & NAILS",
    "MR.BAG FIX": "MR. BAG FIX",
    "MR. BAG FIX": "MR. BAG FIX",
    "MR.BAG-FIX": "MR. BAG FIX",
    "OLINO CREPE AND TEA": "OLINO CREPE & TEA",
    "OLINO CREPE & TEA": "OLINO CREPE & TEA",
    "P.A.PHONE": "P.A. PHONE",
    "P.A. PHONE": "P.A. PHONE",
    "PET N ME": "PET 'N ME",
    "PET 'N ME": "PET 'N ME",
    "POMELO.": "POMELO",
    "POMELO": "POMELO",
    "RE IT": "RE-IT",
    "RE-IT": "RE-IT",
    "T PARTNER": "T-PARTNER",
    "T.PARTNER": "T-PARTNER",
    "T-PARTNER": "T-PARTNER",
    "WESTERN UNION": "WESTERN UNION",
    "WESTERN-UNION": "WESTERN UNION",

    # === NUMBER / FORMAT VARIANTS ===
    "425 DEEGREE": "425 DEGREE",
    "425 DEGREE": "425 DEGREE",
    "425DEGREE": "425 DEGREE",
    "OPTICAL 88": "OPTICAL 88",
    "OPTICAL88": "OPTICAL 88",
    "52 TOYS": "52 TOYS",
    "52TOYS": "52 TOYS",
    "FUKU MATCHA CROSS 2": "FUKU MATCHA",
    "FUKU MATCHA CROSS2": "FUKU MATCHA",
    "FUKU MATCHAX2": "FUKU MATCHA",
    "FUKU MATCHA": "FUKU MATCHA",
    "TAMNAK THONG 5": "TAMNAK THONG 5",
    "TAMNAKTHONG 5": "TAMNAK THONG 5",
    "TUMNAKTHONG 5": "TAMNAK THONG 5",
    "JETTS 24 HOURS FITNESS": "JETTS 24 HOUR FITNESS",
    "JETTS 24 HOUR FITNESS": "JETTS 24 HOUR FITNESS",

    # === ADIDAS unification ===
    "ADIDAS FACTORY OUTLET": "ADIDAS",
    "ADIDAS KIDS": "ADIDAS",
    "ADIDAS NEO CREDIT": "ADIDAS",
    "ADIDAS ORIGINAL": "ADIDAS",
    "ADIDAS ORIGINALS": "ADIDAS",
    "ADIDAS PERFORMANCE": "ADIDAS",
    "ADIDAS": "ADIDAS",

    # === BRAND NAME + DESCRIPTOR ===
    "CHESTER'S": "CHESTER'S",
    "CHESTER'S GRILL": "CHESTER'S",
    "AMERICAN EAGLE": "AMERICAN EAGLE OUTFITTERS",
    "AMERICAN EAGLE OUTFITTERS": "AMERICAN EAGLE OUTFITTERS",
    "AQUA COSMETIC": "AQUA COSMETICS",
    "AQUA COSMETICS": "AQUA COSMETICS",
    "AUTO1": "AUTO1",
    "AUTO1 (CAR SERVICE)": "AUTO1",
    "BANGKOK BANK (BBL)": "BANGKOK BANK",
    "BANGKOK BANK": "BANGKOK BANK",
    "BEN'S COOKIE": "BEN'S COOKIES",
    "BEN'S COOKIES": "BEN'S COOKIES",
    "BONCHON CHICKEN": "BONCHON",
    "BONCHON": "BONCHON",
    "BOOST JUICE": "BOOST JUICE BAR",
    "BOOST JUICE BAR": "BOOST JUICE BAR",
    "BOOST JUICE BARS": "BOOST JUICE BAR",
    "CATH KIDSTONE": "CATH KIDSTON",
    "CATH KIDSTON": "CATH KIDSTON",
    "CITY TOYS CREDIT": "CITY TOYS",
    "CITY TOYS": "CITY TOYS",
    "COLD STONE": "COLD STONE CREAMERY",
    "COLD STONE CREAMERY": "COLD STONE CREAMERY",
    "GARRETT POPCORN": "GARRETT POPCORN SHOPS",
    "GARRETT POPCORN SHOPS": "GARRETT POPCORN SHOPS",
    "GOVERNMENT SAVING BANK": "GOVERNMENT SAVINGS BANK",
    "GOVERNMENT SAVINGS BANK (GSB)": "GOVERNMENT SAVINGS BANK",
    "GOVERNMENT SAVINGS BANK": "GOVERNMENT SAVINGS BANK",
    "JACK RUSSLE": "JACK RUSSEL",
    "JACK RUSSEL": "JACK RUSSEL",
    "KASIKORN BANK (WISDOM)": "KASIKORN BANK",
    "KASIKORN BANK": "KASIKORN BANK",
    "KRUNGSRI FIRST CHIOCE": "KRUNGSRI FIRST CHOICE",
    "KRUNGSRI FIRST CHOICE": "KRUNGSRI FIRST CHOICE",
    "KRUNG THAI BANK CARD TOUCH": "KRUNG THAI BANK",
    "KRUNG THAI BANK": "KRUNG THAI BANK",
    "SMILE SEASONS DENTAL CLINIC": "SMILE SEASONS DENTAL CLINIC",
    "SMILE SEASON DENTAL CLINIC": "SMILE SEASONS DENTAL CLINIC",
    "SANTA FE' STEAK HOUSE": "SANTA FE' STEAK",
    "SANTA FE' STEAK": "SANTA FE' STEAK",
    "SANTA FE'": "SANTA FE' STEAK",
    "PET LOVER CENTRE": "PET LOVER CENTRE",
    "PET LOVERS CENTRE": "PET LOVER CENTRE",
    "ZEN RESTAURANT": "ZEN JAPANESE RESTAURANT",
    "ZEN JAPANESE RESTAURANT": "ZEN JAPANESE RESTAURANT",
    "BODY SHOP": "THE BODY SHOP",
    "THE BODY SHOP": "THE BODY SHOP",
    "KANNIKAR HEALTHY MASSAGE": "KANNIKAR MASSAGE",
    "KANNIKAR MASSAGE": "KANNIKAR MASSAGE",

    # === CRC / CRG / CENTRAL GROUP STANDARDIZATION ===
    "SUPERSPORTS": "SUPER SPORTS",
    "SUPER SPORTS": "SUPER SPORTS",
    "CENTRAL": "CENTRAL DEPARTMENT STORE",
    "CENTRAL @ CENTRALWORLD": "CENTRAL DEPARTMENT STORE",
    "CENTRAL @ MEGABANGNA": "CENTRAL DEPARTMENT STORE",
    "CRC SPORTS / SUPERSPORTS": "SUPER SPORTS",
    "THAI WATSU": "THAIWATSU",
    "THAIWATSU": "THAIWATSU",
    "TOPS": "TOPS",
    "TOPS FOOD HALL": "TOPS FOOD HALL",
    "TOPS DAILY": "TOPS DAILY",
    "TOPS CARE": "TOPS",
    "B2S": "B2S",
    "B2S THINK SPACE": "B2S",
    "OFFICEMATE": "OFFICEMATE",
    "MATSUKIYO": "MATSUKIYO",
    "POWERBUY": "POWER BUY",
    "POWER BUY": "POWER BUY",
    "BIG C EXTRA": "BIG C",
    "BIG C / GO!": "BIG C",
    "BIG C": "BIG C",
    "BIG CAMERA GALLERIA": "BIG CAMERA",
    "BIG CAMERA": "BIG CAMERA",
    "CENTRAL HOME LOCAL": "CENTRAL HOME",
    "CENTRAL HOME": "CENTRAL HOME",
    "CRC THAI WATSU": "THAIWATSU",
    "CRC SPORTS SUPERSPORTS": "SUPER SPORTS",
    "MISTER DONUT": "MISTER DONUT",
    "KFC": "KFC",
    "AUNTIE ANNE'S / MISTER DONUT": "AUNTIE ANNE'S",
    "PEPPER LUNCH": "PEPPER LUNCH",
    "KATSUYA": "KATSUYA",
    "YOSHINOYA": "YOSHINOYA",
    "OOTOYA": "OOTOYA",
    "SOMTAM NUA": "SOMTAM NUA",
    "CHABUTON": "CHABUTON",
    "SALAD FACTORY": "SALAD FACTORY",
    "SHINKANZEN SUSHI": "SHINKANZEN SUSHI",
    "KUB KAO KUB PLA": "KUB KAO KUB PLA",
    "NICE TWO MEAT U": "NICE TWO MEAT U",
    "GUSS DAMN GOOD": "GUSS DAMN GOOD",

    # === SPECIALTY / MISC ===
    "COCO ICHIBANYA": "COCO ICHIBANYA",
    "LAEM CHAROEN SEAFOOD": "LAEM CHAROEN SEAFOOD",
    "LEAM CHAROEN SEAFOOD": "LAEM CHAROEN SEAFOOD",
    "CHARLES & KEITH": "CHARLES & KEITH",
    "TMB THANACHART BANK": "TMB THANACHART BANK",
    "TTB TMBTHANACHART": "TMB THANACHART BANK",
    "POTATO CORNER": "POTATO CORNER",
    "STARBUCKS COFFEE": "STARBUCKS COFFEE",
    "STARBUCKS RESERVE COFFEE": "STARBUCKS COFFEE",
    "SWENSEN'S": "SWENSEN'S",
    "MK RESTAURANTS": "MK RESTAURANT",
    "MK RESTAURANT": "MK RESTAURANT",
    "FUJI JAPANESE RESTAURANT": "FUJI",
    "FUJI": "FUJI",
    "MO-MO-PARADISE": "MO-MO-PARADISE",
    "THE PIZZA COMPANY": "THE PIZZA COMPANY",
    "THE NORTH FACE / VANS": "THE NORTH FACE",
    "THE NORTH FACE": "THE NORTH FACE",
    "PRANAKORN BOAT NOODLE": "PRANAKORN BOAT NOODLE",
    "PRANAKORN NOODLE RESTAURANT ก๋วยเตี๋ยวเรือพระนคร": "PRANAKORN BOAT NOODLE",
    "SUKISHI KOREAN CHARCOAL GRILL": "SUKISHI KOREAN CHARCOAL GRILL",
    "HAI DI LAO HOT POT": "HAI DI LAO",
    "HAI DI LAO": "HAI DI LAO",
    "INTHANIN COFFEE": "INTHANIN COFFEE",
    "INTHANIN": "INTHANIN COFFEE",
    "SUPER RICH": "SUPER RICH",
    "SUPER RICH THAILAND": "SUPER RICH THAILAND",
    "SUPER RICH INTERNATIONAL EXCHANGE(1965)": "SUPER RICH",
    "HUA SENG HONG": "HUA SENG HONG",
    "BOON TONG KEE": "BOON TONG KEE",
    "YOGURT LAND": "YOGURT LAND",
    "YOU & I SUKI": "YOU & I SUKI",
    "DR. PONG": "DR. PONG",
    "DR.PONG X BEAUTILAB": "DR. PONG",
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
    "CC DOUBLE O": "CC DOUBLE O",
    "CPS CHAPS": "CPS CHAPS",
    "CPS": "CPS CHAPS",
    "CPS MEN": "CPS CHAPS",
    "KT OPTIC": "KT OPTIC",
    "SLC CLINIC": "SLC CLINIC",
    "TO B 1 HAIR STATION": "TO B 1 HAIR STATION",
    "KEY & SHOES SERVICE": "KEY & SHOES SERVICE",
    "HANGTHONG WHANG TOH KANG YAOWARAJ": "HANGTHONG WHANG TOH KANG YAOWARAJ",
    "YOMIE'S RICE X YOGURT": "YOMIE'S RICE X YOGURT",
    "MATH TALENT": "MATH TALENT BY DR. YING",
    "MATH TALENT BY DR. YING & CODE GENIUS": "MATH TALENT BY DR. YING",
    "MATH TALENT BY DR. YINGNATIONAL SCHOOL": "MATH TALENT BY DR. YING",
    "MATH TALENT BY DR. YING": "MATH TALENT BY DR. YING",
    "PULL & BEAR": "PULL & BEAR",
    "FIRE TIGER BY SEOULCIAL CLUB": "FIRE TIGER BY SEOULCIAL CLUB",
    "BB BEYOND": "BB BEYOND D-BOX",
    "BB BEYOND D-BOX": "BB BEYOND D-BOX",
    "LEGO CERTIFIED STORE": "LEGO CERTIFIED STORE",
    "UOB EXPRESS": "UOB",
    "UOB": "UOB",
    "UOB WEATH BANKING": "UOB",
    "UOB PRIVILEGE BANKING CENTRE": "UOB",
    "LEVI'S": "LEVI'S",
    "BEARD PAPA'S": "BEARD PAPA'S",
    "BEARD'S PAPA": "BEARD PAPA'S",
    "KIEHL'S": "KIEHL'S",
    "L'OCCITANE": "L'OCCITANE",
    "MARKS & SPENCER": "MARKS & SPENCER",
    "VICTORIA'S SECRET": "VICTORIA'S SECRET",
    "MC DONALD'S": "MC DONALD'S",
    "MCDONALD'S": "MC DONALD'S",
    "KRUNGSRI FIRST CHOICE": "KRUNGSRI FIRST CHOICE",
    "SF BRAND NAME": "SF BRAND NAME",
    "BIG MAC DIGITAL PRINTING": "BIG MAC DIGITAL PRINTING",
    "EYE LAB": "EYE LAB EXCLUSIVE",
    "EYE LAB EXCLUSIVE": "EYE LAB EXCLUSIVE",
    "DR. SMOOTH LIFE": "DR. SMOOTH LIFE",
    "AES CLASS CLINIC": "AES CLASS CLINIC",
    "PIM @ POST": "PIM @ POST",
    "MASSAGE CHAIR NXN": "MASSAGE CHAIR NXN",
    "JING JAI MARKET": "JING JAI MARKET",
    "S. B. FURNITURE": "S. B. FURNITURE",
    "STYLE BALA SHOP": "STYLE BALA SHOP",
    "YALE SMART SHOP": "YALE SMART SHOP",
    "PINK SHARK CAR WASH": "PINK SHARK CAR WASH",
    "BOOTS JUICE": "BOOTS",
    "BOOTS": "BOOTS",
    "CURIOO KIDS": "CURIOO KIDS",
    "CURIOO": "CURIOO KIDS",
    "CURIOOKIDS": "CURIOO KIDS",
    "CURIOOKIDS THAILAND": "CURIOO KIDS",
    "HAOLE CHINESE LANGUAGE SCHOOL": "HAOLE",
    "HAOLE": "HAOLE",
    "JAY MART IOT": "JAYMART",
    "JAY MART": "JAYMART",
    "JAYMART IOT": "JAYMART",
    "JAYMART SMART PHONE&TABLET": "JAYMART",
    "JAYMART": "JAYMART",
    "SUSHI DEN": "SUSHI DEN",
    "DON BY SUSHI DEN": "SUSHI DEN",
    "CLICKROBOT": "CLICKROBOT",
    "CLICKROBOTS": "CLICKROBOT",
    "CHEESY FRIED SNACK": "CHEESY FRIED SNACKS",
    "CHEESY FRIED SNACKS": "CHEESY FRIED SNACKS",
    "DOSH (DESCENDANT OF SUPERHEROES)": "DOSH (DESCENDANT OF SUPERHEROES)",
    "EXPERT WATCH": "EXPERT WATCH",
    "FOCUS SHOP": "FOCUS",
    "FOCUS STORE": "FOCUS",
    "FOCUS": "FOCUS",
    "HACHIBAN": "HACHIBAN RAMEN",
    "HACHIBAN RAMEN": "HACHIBAN RAMEN",
    "IT BY IT CITY": "IT CITY",
    "IT CITY ACE": "IT CITY",
    "IT CITY": "IT CITY",
    "IT CITY MOBILE": "IT CITY",
    "JOSILINS": "JOSILIN",
    "JOSILIN": "JOSILIN",
    "LYN AROUND COLLECTIBLE": "LYN AROUND",
    "LYN AROUND": "LYN AROUND",
    "LYN INFINITE": "LYN",
    "LYN BEAUTY": "LYN BEAUTY",
    "MOSHI AVA": "MOSHI MOSHI",
    "MOSHI MOSHI": "MOSHI MOSHI",
    "QQ DESSERT": "QQ DESSERT",
    "QQ DESSERT SEATING": "QQ DESSERT",
    "QQ HEALTHY DESSERT": "QQ DESSERT",
    "S&P BAKERY": "S&P",
    "S&P": "S&P",
    "S&P SIMPLY DELICIOUS": "S&P",
    "SAMSONITE RED": "SAMSONITE",
    "SAMSONITE": "SAMSONITE",
    "SAMSUNG MOBILE": "SAMSUNG",
    "SAMSUNG": "SAMSUNG",
    "SEIKO CLOCK": "SEIKO",
    "GRAND SEIKO": "GRAND SEIKO",
    "SHU": "SHU UEMURA",
    "SHU UEMURA": "SHU UEMURA",
    "SKECHERS": "SKECHERS",
    "SKECHERS FOAMIES": "SKECHERS",
    "STARBUCKS": "STARBUCKS COFFEE",
    "SUPER SPORTS ACTIVE": "SUPER SPORTS",
    "TIGER": "TIGER",
    "ONITSUKA TIGER": "ONITSUKA TIGER",
    "TRUE SPHERE": "TRUE",
    "TRUE": "TRUE",
    "DANCE PLUS ACADEMY": "DANCE PLUS",
    "DANCE PLUS": "DANCE PLUS",
    "CLAUDIA KLEID BLACK&WHITE": "CLAUDIA KLEID",
    "CLAUDIA KLEID WEEKEND": "CLAUDIA KLEID",
    "CLAUDIA KLEID": "CLAUDIA KLEID",
    "VANS": "VANS",
    "THE NORTH FACE / VANS": "THE NORTH FACE",
    "KHAWMONKAISINGKAPRO": "KHAWMONKAISINGKAPRO",
    "BUNNY SHAKE CAFE": "BUNNY SHAKE",
    "BUNNY SHAKE": "BUNNY SHAKE",
    "COCONUT": "COCONUT",
    "DEFRY 01": "DEFRY 01",
    "BSC COSMETOLOGY": "BSC",
    "BSC": "BSC",
    "AIS BY JAY MART": "AIS",
    "AIS DIGITAL ARENA": "AIS",
    "AIS SERENADE CLUB": "AIS",
    "AIS SERENADE": "AIS",
    "AIS SHOP": "AIS",
    "AIS": "AIS",
    "DTAC HALL": "DTAC",
    "DTAC SHOP": "DTAC",
    "DTAC": "DTAC",
    "I CARE": "I CARE",
    "HI CARE": "I CARE",
    "MLAB (ON RUNNING)": "MLAB",
    "MLAB": "MLAB",
    "NF PHONE": "NF PHONE",
    "T2C CURRENCY EXCHANGE": "T2C CURRENCY EXCHANGE",
    "DIOR BACKSTAGE/DIOR": "DIOR",
    "DIOR": "DIOR",
    "CHRISTIAN DIOR": "DIOR",
    "SENSE BY SOS": "SENSE BY SOS",
    "CMP GROUP": "CMP",
    "CMP": "CMP",
    "DKNY AND CK": "DKNY AND CK",
    "BOSS HUGO BOSS": "HUGO BOSS",
    "HUGO BOSS": "HUGO BOSS",
    "BOSS": "HUGO BOSS",
    "BOSSINI": "BOSSINI",
    "LUCKY": "LUCKY",
    "LUCKY 13 SANDWICH": "LUCKY 13 SANDWICH",
    "LUCKY MILK": "LUCKY MILK",
    "LUCKY MILK & TEA": "LUCKY MILK",
    "LUCKY SUKI": "LUCKY SUKI",
    "LUCKY WARE": "LUCKY WARE",
    "GLUCKY MASK": "GLUCKY MASK",
    "IROHA RAMEN": "IROHA RAMEN",
    "A RAMEN": "IROHA RAMEN",
    "THE PIZZA COMPANY": "THE PIZZA COMPANY",
    "SUSHI EXPRESS": "SUSHI EXPRESS",
    "SUSHIRO": "SUSHIRO",
    "ZENFRY": "ZENFRY",
    "VAVA FROZEN YOGURT": "VAVA FROZEN YOGURT",
    "DONKI": "DONKI",
    "SALMON FOR YOU": "SALMON FOR YOU",
    "FOR YOU": "FOR YOU",
    "DIAMOND FOR YOU": "DIAMOND FOR YOU",
    "PONN CAFE": "PONN CAFE",
    "PRONTO": "PRONTO",
    "PRONTO DENIM": "PRONTO",
    "BAAN YING": "BAAN YING CAFE & MEAL",
    "BAAN YING CAFE & MEAL": "BAAN YING CAFE & MEAL",
    "CENTRAL EDITION": "CENTRAL EDITION",
    "CENTRAL FOOD HALL": "CENTRAL FOOD HALL",
    "CENTRAL LOVE THE EARTH": "CENTRAL LOVE THE EARTH",
    "CENTRAL POST": "CENTRAL POST",
    "CENTRAL PLAZA NAKORNSRITHAMMARAT POSTAL COUNTER": "CENTRAL POST",
    "BEARHOUSE": "BEARHOUSE",
    "BEARHOUSE DESSERT AND MILK TEA": "BEARHOUSE",
    "H&M HOME": "H&M",
    "H&M": "H&M",
    "GSP SPORT": "GSP",
    "GSP": "GSP",
    "IT'S SKIN": "IT'S SKIN",
    "SKIN": "IT'S SKIN",
    "TIME": "TIME",
    "TIME CLINIC": "TIME CLINIC",
    "TIME STORE": "TIME",
    "TOKYO SWEET": "TOKYO SWEET",
    "MAKAI ACAI & SUPERFOOD BAR": "MAKAI ACAI & SUPERFOOD BAR",
    "HIDRATESPARK": "HIDRATESPARK",
    "NATURE REPUBLIC": "NATURE REPUBLIC",
    "SLEEPING CLOUD": "SLEEPING CLOUD",
    "THE KLINIQUE": "THE KLINIQUE",
    "WACOAL": "WACOAL",
    "WORKING WOMAN": "WORKING WOMAN",
    "ALDO": "ALDO",
    "WHAN MOBILE": "WHAN MOBILE",
    "NANA NAIL": "NANA NAIL",
    "BANANA NAIL": "BANANA NAIL",
    "IT BANANA": "BANANA",
    "BANANA MOBILE": "BANANA",
    "BANANA IT": "BANANA",
    "BANANA OUTLET": "BANANA",
    "BANANA": "BANANA",
    # === ADDITIONAL NORMALIZATION (from user feedback) ===
    "AEON THANA SINSAP": "AEON",
    "AEON": "AEON",
    "ARI FOOTBALL CONCEPT STORE": "ARI FOOTBALL",
    "ARI FOOTBALL": "ARI FOOTBALL",
    "EYE CLASS": "EYE CLASS",
    "EYE CLASS BY TOP CHAROEN": "EYE CLASS",
    "FOODPARK": "FOOD PARK",
    "FOOD PARK": "FOOD PARK",
    "FOODPATIO": "FOOD PATIO",
    "FOOD PATIO": "FOOD PATIO",
    "GANGNAM": "GANGNAM CLINIC",
    "GANGNAM CLINIC": "GANGNAM CLINIC",
    "JUBILEE": "JUBILEE DIAMOND",
    "JUBILEE DIAMOND": "JUBILEE DIAMOND",
    "JUBILEE INSPIRES": "JUBILEE DIAMOND",
    "KPN": "KPN MUSIC ACADEMY",
    "KRUNGTHAI": "KRUNGTHAI BANK",
    "KRUNGTHAI BANK": "KRUNGTHAI BANK",
    "ลาวญวน": "LAO YUAN",
    "LUXURY หมอนโรงแรม 6 ดาว": "LUXURY",
    "LUXURY": "LUXURY",
    "MIKI MIKI STORE": "MIKI MIKI",
    "MIKI MIKI": "MIKI MIKI",
    "NITIPON": "NITIPON CLINIC",
    "NITIPON CLINIC": "NITIPON CLINIC",
    "PROCLEAN": "PRO CLEAN",
    "PRO CLEAN": "PRO CLEAN",
    "REAL ME": "REALME",
    "REALME": "REALME",
    "SE-ED BOOK CENTER": "SE-ED",
    "SE-ED": "SE-ED",
    "SHANE ENGLISH SCHOOL THAILAND": "SHANE ENGLISH SCHOOL",
    "SHANE ENGLISH SCHOOL": "SHANE ENGLISH SCHOOL",
    "SHANE ENGLISH SCHOOL & DIRECT ENGLISH": "SHANE ENGLISH SCHOOL",
    "TUMRABTHAI": "TUMRUBTHAI",
    "TUMRUBTHAI": "TUMRUBTHAI",
    "YAOWARAJ KRUNGTHEP": "YAOWARAT KRUNGTHEP",
    "YAOWARAT KRUNGTHEP": "YAOWARAT KRUNGTHEP",
    "GQ SOCKS": "GQ",
    "GQ UNDERWEAR": "GQ",
    "GQ": "GQ",
    "GQ JEANS": "GQ",

    # === ROUND 2 NORMALIZATION ===
    "DAKASI": "DAKASHI",
    "DAKASI MILKTEA": "DAKASHI",
    "DAKASI TAIWANESE DESSERT": "DAKASHI",
    "DAKASHI": "DAKASHI",
    "CLADIA KLEID": "CLADIA KLEID",
    "CLAUDIA KLEID": "CLADIA KLEID",
    "CLAUDIA KLEID BLACK&WHITE": "CLADIA KLEID",
    "CLAUDIA KLEID WEEKEND": "CLADIA KLEID",
    "CENTRAL HOME": "CENTRAL DEPARTMENT STORE",
    "CENTRAL HOME LOCAL": "CENTRAL DEPARTMENT STORE",
    "CENTRAL LOVE THE EARTH": "CENTRAL DEPARTMENT STORE",
    "DISNEY HOOYAY": "DISNEY",
    "DISNEY INTERVISION": "DISNEY",
    "DISNEY JEANS": "DISNEY",
    "DISNEY KIDDO": "DISNEY",
    "DISNEY PRINCESS": "DISNEY",
    "DISNEY TAKETOYS": "DISNEY",
    "DISNEY TOYS": "DISNEY",
    "MEYER DISNEY": "DISNEY",
    "DISNEY": "DISNEY",
    "HELLO KITTY WD": "HELLO KITTY",
    "HELLO WD": "HELLO KITTY",
    "HELLO KITTY": "HELLO KITTY",
    "INFINITY MEDICAL CLINIC": "INFINITY",
    "INFINITY": "INFINITY",
    "KT": "KT OPTIC",
    "LE COQ SPORTIF (APPAREL)": "LE COQ SPORTIF",
    "LE COQ SPORTIF (FOOTWEAR)": "LE COQ SPORTIF",
    "LE COQ SPORTIF": "LE COQ SPORTIF",
    "MAMAS&PAPAS": "MAMAS & PAPAS",
    "MAMAS & PAPAS": "MAMAS & PAPAS",
    "MANEE ME MORE": "MANEE ME MORE",
    "MANEE": "MANEE ME MORE",
    "MOSHI": "MOSHI MOSHI",
    "URBANAKTIV": "URBAN AKTIV",
    "URBAN AKTIV": "URBAN AKTIV",
    "KTB": "KRUNGTHAI BANK",
}

# Build NORM for fast lookup — upper-cased keys
NORM_FAST = {k.upper().strip(): v for k, v in NORM.items()}

# Tenants to drop entirely
DROP = {"IKEA", "NAD", "NADO"}


def canonical(name):
    """Convert ANY tenant name to its canonical form."""
    name = name.strip()
    key = name.upper()
    # 1. Direct check
    if key in NORM_FAST:
        return NORM_FAST[key]
    # 2. Collapse all whitespace and re-check
    collapsed = re.sub(r'\s+', ' ', key)
    if collapsed != key and collapsed in NORM_FAST:
        return NORM_FAST[collapsed]
    # 3. Strip punctuation/hyphens and re-check
    stripped = re.sub(r"[\-'’\u2019.]", '', collapsed)
    stripped = re.sub(r'\s+', ' ', stripped).strip()
    if stripped != key and stripped in NORM_FAST:
        return NORM_FAST[stripped]
    # 4. Handle THAI names — check if the English portion matches a canonical
    if re.search(r'[\u0E00-\u0E7F]', name):
        # Extract the English part before the Thai text
        match = re.match(r'^([A-Za-z\s&\'.,()/-]+)', key)
        if match:
            eng_part = match.group(1).strip()
            if eng_part in NORM_FAST:
                return NORM_FAST[eng_part]
    # Fallback: UPPERCASE with collapsed spaces
    return collapsed


def norm_category(cat):
    """Normalize category to standard labels."""
    c = cat.strip().upper()
    food_patterns = ['FOOD', 'BEVERAGE', 'RESTAURANT', 'DINING', 'CAFE', 'DRINK', 'BAKERY', 'DESSERT']
    fashion_patterns = ['FASHION', 'APPAREL', 'CLOTHING', 'WEAR', 'GARMENT']
    beauty_patterns = ['BEAUTY', 'WELLNESS', 'SPA', 'COSMETIC', 'SALON', 'CLINIC', 'HEALTH', 'MASSAGE', 'DENTAL']
    bank_patterns = ['BANK', 'FINANCE', 'FINANCIAL', 'INSURANCE', 'CURRENCY', 'EXCHANGE', 'INVESTMENT', 'CREDIT', 'MONEY']
    tech_patterns = ['TECHNOLOGY', 'MOBILE', 'PHONE', 'TELECOM', 'COMPUTER', 'GADGET', 'IT ', ' CAMERA', 'ELECTRONIC']
    entertainment_patterns = ['ENTERTAINMENT', 'CINEMA', 'CINEPLEX', 'THEATRE', 'THEATER', 'GAME', 'PLAY', 'KIDS', 'FUN']
    lifestyle_patterns = ['LIFESTYLE', 'LIVING', 'HOME', 'FURNITURE', 'DECOR', 'GIFT', 'SOUVENIR', 'BOOK', 'STATIONERY', 'TOY', 'SPORT', 'JEWELRY', 'WATCH', 'OPTICAL', 'PET', 'SERVICE']
    education_patterns = ['EDUCATION', 'SCHOOL', 'LEARNING', 'ACADEMY', 'STUDIO', 'MUSIC', 'LANGUAGE', 'TUTOR']

    if any(p in c for p in food_patterns):
        return 'Food & Beverage'
    if any(p in c for p in beauty_patterns):
        return 'Beauty & Wellness'
    if any(p in c for p in bank_patterns):
        return 'Bank & Financial Services'
    if any(p in c for p in tech_patterns):
        return 'Technology & Electronics'
    if any(p in c for p in entertainment_patterns):
        return 'Entertainment'
    if any(p in c for p in education_patterns):
        return 'Services & Education'
    if any(p in c for p in fashion_patterns):
        return 'Fashion & Apparel'
    if any(p in c for p in lifestyle_patterns):
        return 'Lifestyle & Specialty'
    return c.title()  # fallback


# ─── Apply to all CSV files ─────────────────────────────────────────────
mall_files = glob.glob(os.path.join(DATA_DIR, "Central*.csv")) + [os.path.join(DATA_DIR, "MegaBangna.csv")]

all_before = set()
all_after = set()
edges = []

for fpath in sorted(mall_files):
    with open(fpath, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()
    hdr_idx = 0
    for i, l in enumerate(lines):
        if l.strip().startswith("Source") and "Target" in l:
            hdr_idx = i
            break
    preamble = lines[:hdr_idx]
    csv_lines = lines[hdr_idx:]

    reader = csv.DictReader(csv_lines)
    out_rows = []
    for row in reader:
        if None in row or row.get("Source") is None or row.get("Target") is None:
            continue
        raw = row["Source"].strip()
        canon = canonical(raw)
        cat = norm_category(row.get("Category", ""))
        if canon in DROP:
            continue
        row["Source"] = canon
        row["Category"] = cat
        out_rows.append(row)
        all_before.add(raw)
        all_after.add(canon)
        edges.append((canon, row["Target"].strip(), cat))

    with open(fpath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Source", "Target", "Weight", "Floor", "Category"])
        for line in preamble:
            f.write(line + "\n")
        writer.writeheader()
        for row in out_rows:
            writer.writerow(row)

    print(f"  {os.path.basename(fpath):40s} {len(out_rows):5d} rows")

print(f"\nBefore: {len(all_before)} unique variants")
print(f"After:  {len(all_after)} unique canonicals")

# Report merges
from collections import Counter
before_cnt = Counter()
for t in all_before:
    before_cnt[t] += 1

merge_map = defaultdict(set)
for t in all_before:
    merge_map[canonical(t)].add(t)

print("\n=== MERGED GROUPS ===")
for canon_name, variants in sorted(merge_map.items(), key=lambda x: -len(x[1])):
    if len(variants) > 1:
        print(f"  {canon_name}:")
        for v in sorted(variants, key=lambda x: -before_cnt[x]):
            print(f"    <- {v} ({before_cnt[v]}x)")

print("\nDone! All tenant names and categories normalized.")
