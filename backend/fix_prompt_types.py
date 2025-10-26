#!/usr/bin/env python3
"""
Fix prompt types in Firestore to use simplified taxonomy:
- summary: Any candidate summary/brief
- email: Any email content

Runs in dry-run mode by default.
"""

from google.cloud import firestore
from datetime import datetime
import argparse

db = firestore.Client()

# Type mapping rules
TYPE_MAPPING = {
    'recruitment': 'summary',
    'anonymous': 'summary',
    'candidate-submission': 'email',
    'email-summary-using-summaries': 'email',
    'email': 'email',  # Keep as-is
}

def fix_prompt_types(dry_run=True):
    """Fix all prompt types to use simplified taxonomy"""
    
    print("🔍 Scanning prompts in Firestore...")
    
    prompts = list(db.collection('prompts').stream())
    updates_needed = []
    
    for doc in prompts:
        data = doc.to_dict()
        current_type = data.get('type')
        new_type = TYPE_MAPPING.get(current_type, current_type)
        
        changes = {}
        
        # Check if type needs updating
        if new_type != current_type:
            changes['type'] = {
                'old': current_type,
                'new': new_type
            }
        
        # Special case: summary-for-platform-v2 should be default
        if doc.id == 'summary-for-platform-v2' and not data.get('is_default'):
            changes['is_default'] = {
                'old': data.get('is_default', False),
                'new': True
            }
        
        if changes:
            updates_needed.append({
                'doc_id': doc.id,
                'name': data.get('name'),
                'changes': changes
            })
    
    if not updates_needed:
        print("✅ No updates needed - all types are correct!")
        return
    
    print(f"\n📊 Found {len(updates_needed)} prompts that need updates:\n")
    
    for update in updates_needed:
        print(f"📄 {update['name']} ({update['doc_id']})")
        for field, change in update['changes'].items():
            print(f"   {field}: '{change['old']}' → '{change['new']}'")
        print()
    
    if dry_run:
        print("🔍 DRY RUN - No changes made")
        print("Run without --dry-run to apply these changes")
        return
    
    # Apply updates
    print("🚀 Applying updates...")
    
    for update in updates_needed:
        doc_ref = db.collection('prompts').document(update['doc_id'])
        
        update_data = {
            'updated_at': datetime.utcnow().isoformat() + 'Z',
            'updated_by': 'fix_types_script'
        }
        
        for field, change in update['changes'].items():
            update_data[field] = change['new']
        
        doc_ref.update(update_data)
        print(f"   ✅ Updated {update['name']}")
    
    print(f"\n🎉 Successfully updated {len(updates_needed)} prompts!")
    print("\n📊 Final type distribution:")
    
    # Show final counts
    all_prompts = list(db.collection('prompts').stream())
    type_counts = {}
    for doc in all_prompts:
        t = doc.to_dict().get('type', 'unknown')
        type_counts[t] = type_counts.get(t, 0) + 1
    
    for t, count in sorted(type_counts.items()):
        print(f"   {t}: {count}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fix prompt types in Firestore')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='Show what would be changed without making changes (default)')
    parser.add_argument('--apply', action='store_true',
                       help='Actually apply the changes')
    
    args = parser.parse_args()
    
    # If --apply is specified, turn off dry_run
    dry_run = not args.apply
    
    if dry_run:
        print("=" * 80)
        print("DRY RUN MODE")
        print("=" * 80)
    
    fix_prompt_types(dry_run=dry_run)
    
    if dry_run:
        print("\n" + "=" * 80)
        print("To apply these changes, run: python fix_prompt_types.py --apply")
        print("=" * 80)
