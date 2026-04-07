#!/usr/bin/env python3
import json
import sys

if len(sys.argv) < 2:
    print("Usage: show_features.py <feature_list.json>")
    sys.exit(1)

with open(sys.argv[1]) as f:
    data = json.load(f)

for feat in data['features']:
    status_icon = '✅' if feat['status'] == 'done' else '⏳' if feat['status'] == 'in_progress' else '⬜'
    print(f"{status_icon} {feat['id']}: {feat['title']} [{feat['status']}]")

print("")
print("=== Next Recommended Feature ===")
done_ids = {f['id'] for f in data['features'] if f['status'] == 'done'}
for feat in data['features']:
    if feat['status'] != 'done':
        deps = feat.get('depends_on', [])
        if all(d in done_ids for d in deps):
            print(f"→ {feat['id']}: {feat['title']}")
            break
