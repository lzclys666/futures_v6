with open(r'C:\Users\Administrator\.qclaw\workspace-agent-63961edb\scripts\macro_history_backfill.py', encoding='utf-8') as f:
    content = f.read()

# Find proxy handler
search = 'elif proxy == "lme_cu_inventory_inv":'
idx = content.find(search)
print('Handler at:', idx)
if idx >= 0:
    print(content[idx:idx+400])
else:
    print('NOT FOUND!')

print()
# Check AG return section has new fields
idx2 = content.find('ag_au_real_ratio')
print('ag_au_real_ratio at:', idx2)
if idx2 >= 0:
    print(content[idx2-50:idx2+200])
