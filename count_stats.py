import csv, glob, os
DATA_DIR = r'C:\DADS7201\PJ_MIDTERM\Data'
mall_files = glob.glob(DATA_DIR + '/Central*.csv') + [DATA_DIR + '/MegaBangna.csv']
tenants = set()
malls = set()
for fpath in mall_files:
    with open(fpath, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()
    hdr_idx = 0
    for i, l in enumerate(lines):
        if l.strip().startswith('Source') and 'Target' in l:
            hdr_idx = i
            break
    for l in lines[hdr_idx+1:]:
        l = l.strip()
        if not l or l == '```':
            continue
        parts = l.split(',')
        if len(parts) >= 2:
            tenants.add(parts[0].strip())
            malls.add(parts[1].strip())
print(f'Total unique tenants: {len(tenants)}')
print(f'Total unique malls: {len(malls)}')
