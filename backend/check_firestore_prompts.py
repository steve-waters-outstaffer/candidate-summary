#!/usr/bin/env python3
"""Quick diagnostic to see what prompts are in Firestore"""

from google.cloud import firestore

db = firestore.Client()

print("=" * 80)
print("PROMPTS IN FIRESTORE")
print("=" * 80)

prompts = db.collection('prompts').stream()

for doc in prompts:
    data = doc.to_dict()
    print(f"\nDocument ID: {doc.id}")
    print(f"  name: {data.get('name')}")
    print(f"  category: {data.get('category')}")
    print(f"  type: {data.get('type')}")
    print(f"  enabled: {data.get('enabled')}")
    print(f"  is_default: {data.get('is_default')}")
    print(f"  sort_order: {data.get('sort_order')}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

# Group by type
by_type = {}
all_prompts = list(db.collection('prompts').stream())
for doc in all_prompts:
    data = doc.to_dict()
    t = data.get('type', 'unknown')
    if t not in by_type:
        by_type[t] = 0
    by_type[t] += 1

print(f"\nTotal prompts: {len(all_prompts)}")
print("\nBy type:")
for t, count in sorted(by_type.items()):
    print(f"  {t}: {count}")

# Group by category
by_category = {}
for doc in all_prompts:
    data = doc.to_dict()
    c = data.get('category', 'unknown')
    if c not in by_category:
        by_category[c] = 0
    by_category[c] += 1

print("\nBy category:")
for c, count in sorted(by_category.items()):
    print(f"  {c}: {count}")
