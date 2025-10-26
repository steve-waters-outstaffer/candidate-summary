#!/usr/bin/env python3
"""
Migration Script: JSON Files + prompts.py → Firestore

Migrates all prompt configurations from:
- backend/single-candidate-prompts/**/*.json
- backend/multiple-candidates-prompts/*.json  
- backend/config/prompts.py (hardcoded prompt)

To Firestore collections:
- prompts/
- webhook_config/

Usage:
    python migrate_prompts_to_firestore.py [--dry-run]
"""

import os
import json
import re
from datetime import datetime
from pathlib import Path
from google.cloud import firestore
import argparse

# Initialize Firestore
db = firestore.Client()

def slugify(name):
    """Convert prompt name to slug for document ID"""
    slug = name.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')

def extract_type_from_path(filepath):
    """Extract type from file path (e.g., 'email', 'recruitment', 'anonymous')"""
    parts = Path(filepath).parts
    if 'email' in parts:
        return 'email'
    elif 'recruitment' in parts:
        return 'recruitment'
    elif 'anonymous' in parts:
        return 'anonymous'
    else:
        # Use filename without extension
        return Path(filepath).stem.replace('_', '-')

def migrate_json_prompt(filepath, category, sort_order_start):
    """Migrate a single JSON prompt file to Firestore format"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    name = data.get('name', Path(filepath).stem.replace('_', ' ').title())
    slug = slugify(name)
    
    prompt_doc = {
        'name': name,
        'slug': slug,
        'description': data.get('description', ''),
        'category': category,
        'type': extract_type_from_path(filepath),
        'enabled': data.get('enabled', True),
        'is_default': data.get('is_default', False),
        'sort_order': data.get('sort_order', sort_order_start),
        'system_prompt': data.get('system_prompt', ''),
        'template': data.get('template', ''),
        'user_prompt': data.get('user_prompt', ''),
        'created_at': datetime.utcnow().isoformat() + 'Z',
        'updated_at': datetime.utcnow().isoformat() + 'Z',
        'created_by': 'migration_script',
        'updated_by': 'migration_script'
    }
    
    return slug, prompt_doc

def migrate_hardcoded_prompt():
    """Migrate the hardcoded 'Summary For Platform V2' prompt from prompts.py"""
    
    # This is the prompt currently in prompts.py
    name = "Summary For Platform V2"
    slug = slugify(name)
    
    system_prompt = """**Role:** Produce polished, decision-ready one-page candidate briefs for Outstaffer's ATS.
**Audience:** Senior managers/clients reviewing a curated shortlist.
**Tone:** Professional, concise, recruiter-curated. No emojis.
**Output:** One HTML block only (no plaintext outside of HTML).

**Handling Edits & Overrides:**
- The 'ADDITIONAL CONTEXT' field is for post-generation edits and overrides. Treat any instructions here as a final command that must be followed.
- When this field contains instructions (e.g., "Remove X", "Rephrase Y", "Add a bullet about Z"), re-generate the entire brief from the source data, applying the requested modification perfectly.
- These instructions have the highest priority and override conflicting information from any other source.

**Source weighting (when evidence conflicts):**
1) **ADDITIONAL CONTEXT (User Edits):** Final instructions for modification. Highest priority.
2) **Recruiter-led interview** = primary. Trust this first for nuance, validation of skills, personality/culture fit.
3) **Candidate CV/Resume File:** Foundational source for career history, dates, and technical abilities.
4) **Candidate Data (RecruitCRM) + Job Description** = factual baseline.
5) **AI Interview Assessment** = secondary signal only. If it conflicts with recruiter notes, **defer to the recruiter**.

**JD coverage (role-agnostic):**
- When deriving **Key Qualifications**, **JD Alignment**, and **Key Considerations**, evaluate **both** technical requirements (skills, tools, certifications, domain knowledge) **and** non-technical requirements (leadership, change/transformation, stakeholder management, cultural/values fit, strategic scope, communication, etc.) **as expressed in the JD**.
- Weight emphasis **in proportion to the JD** (e.g., if the JD stresses leadership more than tools, reflect that in what you surface).

**Fallback logic (when inputs are thin/missing):**
- If the recruiter interview is missing or sparse, rely on Candidate Data + JD. If a claim cannot be supported, **omit it**.
- If a JD requirement (technical or non-technical) is **not evidenced** in sources, surface it as a **Key Consideration** (gap/unknown) rather than inferring.
- If dates/titles are inconsistent across sources, use RecruitCRM as canonical and note uncertainty in **Key Considerations**.
- **Never invent details. Prefer silence to speculation.**

**Synthesize, don't recite:** Critically combine sources using the weighting above. Your summary must reflect the deepest understanding gained from the recruiter-led interview.

**Derive Key Points:** Rows in **Key Qualifications** and **Key Considerations** must be derived for this candidate & role (no boilerplate).

**Formatting rules**
* Use Inter font via inline `<style>` (Google Fonts import). Ensure `h4` is bold (`font-weight: 700;`).
* Use `<h4>` for section headings.
* Do not include candidate name/title/header metadata (ATS already shows it).
* Do not use dashes/hyphens in dates, ranges, or salaries. Write ranges as "2018 to 2022" and "PHP 450K to 600K".
* Use `<ul><li>` for lists.
* **Company names in Career Highlights must be bolded using `<strong>` tags (e.g., `<strong>Outstaffer</strong>`), not Markdown.**
* Use the same bordered two-column table for Key Qualifications and Key Considerations.
* In Career Highlights, write dates as "2018 to 2022" and provide a short impact line.
* Close with Recommendation: `<h4>Recommendation – [verdict]</h4><p>[one short sentence on why]</p>`.

**Section order**
1.  Executive Summary (2–3 sentences)
2.  Candidate Snapshot (4–6 bullets)
3.  Key Qualifications (bordered two-column table, 2–4 rows derived from data)
4.  Key Considerations (bordered two-column table, 2–3 rows derived from data)
5.  JD Alignment (3–4 bullets; choose the **most material** JD requirements across technical **and** non-technical, reflecting the JD's emphasis)
6.  Career Highlights (curated list; bold companies; dates "A to B")
7.  Recommendation (heading with verdict, then one short paragraph)

**Judgement guidelines**
* Add context: scope, scale, impact, risks (team sizes, regions, % gains, avoided issues).
* Prioritise the 2–4 most recent & relevant roles; collapse minor early roles if useful.
* Be frank in Considerations (comp band vs budget, scope fit, timing/availability, specific gaps or unproven asks).
* Keep prose tight; avoid filler."""

    template = """<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap');
  body, div, p, ul, li, h4, table, td, th {
    font-family: 'Inter', sans-serif !important; font-size: 14px; line-height: 1.5; color: #222; margin: 0; padding: 0;
  }
  h4 { margin-top: 20px; margin-bottom: 4px; font-weight: 700; }
  ul { margin-left: 20px; margin-bottom: 12px; }
  .brand { font-weight: 500; font-size: 15px; margin-bottom: 12px; }
  .kv-table { width: 100%; border-collapse: collapse; border: 1px solid #ddd; margin-bottom: 12px; }
  .kv-table tr { border-bottom: 1px solid #ddd; }
  .kv-table tr:last-child { border-bottom: none; }
  .kv-table td { padding: 8px 10px; vertical-align: top; }
  .kv-table td.key { width: 28%; font-weight: 600; background: #f9f9f9; border-right: 1px solid #ddd; }
</style>

<div class="brand">[Executive Summary: Synthesize the candidate's core value proposition, key experience level, and overall fit for the role in 2 to 3 sentences.]</div>

<h4>Candidate Snapshot</h4>
<ul>
  <li>[Highest qualification/certification] — [total years] experience.</li>
  <li>[Most relevant recent role and company] (YYYY to YYYY).</li>
  <li>[Key domain exposure, e.g., industries, regions, systems].</li>
  <li>[2 to 3 crisp, impactful achievements from career].</li>
</ul>

<h4>Key Qualifications</h4>
<table class="kv-table">
  <tr><td class="key">[Derived Qualification 1]</td><td>[Describe the candidate's most critical strength based on the JD — this may be technical (skills, tools, domain) **or** non-technical (leadership, change, stakeholder management). Provide evidence.]</td></tr>
  <tr><td class="key">[Derived Qualification 2]</td><td>[Describe another major qualification that makes them a strong contender; reflect the JD's emphasis. Quantify with metrics if possible.]</td></tr>
</table>

<h4>Key Considerations</h4>
<table class="kv-table">
  <tr><td class="key">[Derived Consideration 1]</td><td>[Identify the most significant risk, gap, or unevidenced JD ask (technical or non-technical). Be specific and evidence-based.]</td></tr>
  <tr><td class="key">[Derived Consideration 2]</td><td>[Another concrete consideration such as compensation alignment, availability, relocation, or scope fit.]</td></tr>
</table>

<h4>JD Alignment</h4>
<ul>
  <li>[Alignment 1: Explicitly map to a **material** JD requirement; use the JD's own language where helpful.]</li>
  <li>[Alignment 2: Another material JD requirement (technical or non-technical) with evidence.]</li>
  <li>[Alignment 3: Another material JD requirement with evidence.]</li>
</ul>

<h4>Career Highlights</h4>
<ul>
  <li><strong>[Significant Company]</strong> — [Role] (YYYY to YYYY): [1-line summary of key impact or achievement].</li>
  <li>[List other significant roles here as separate list items...]</li>
  <li>[Summarize earlier, less relevant roles if applicable. OMIT this line entirely if there are no earlier roles to summarize.]</li>
</ul>

<h4>Recommendation</h4>
<p><i>[Choose: Strongly recommended / Recommended / Recommended with reservations]</i> &ndash; [State the final recommendation in one sentence, referencing the primary reason for the decision and any conditions for proceeding.]</p>"""

    user_prompt = """Generate a candidate brief using the following data. Evaluate both technical and non-technical JD requirements; weight emphasis according to the JD; do not speculate — surface unevidenced JD asks under Key Considerations.
**CANDIDATE DATA:**
{candidate_data}
**JOB DESCRIPTION:**
{job_data}
**AI INTERVIEW ASSESSMENT:**
{interview_data}
{interview_section}
**ADDITIONAL CONTEXT:**
{additional_context}
Generate the HTML candidate brief following the exact format and guidelines above."""

    prompt_doc = {
        'name': name,
        'slug': slug,
        'description': 'Professional one-page candidate brief for ATS',
        'category': 'single',
        'type': 'summary',
        'enabled': True,
        'is_default': True,  # This is the default prompt
        'sort_order': 1,
        'system_prompt': system_prompt,
        'template': template,
        'user_prompt': user_prompt,
        'created_at': datetime.utcnow().isoformat() + 'Z',
        'updated_at': datetime.utcnow().isoformat() + 'Z',
        'created_by': 'migration_script',
        'updated_by': 'migration_script'
    }
    
    return slug, prompt_doc

def create_default_webhook_config():
    """Create default webhook configuration"""
    config_doc = {
        'default_prompt_id': 'summary-for-platform-v2',
        'prompt_category': 'single',
        'use_quil': True,
        'use_fireflies': False,
        'additional_context': '',
        'auto_push': False,  # Start with manual review
        'auto_push_delay_seconds': 0,
        'enabled': True,
        'create_tracking_note': False,  # Phase 3 feature
        'max_concurrent_tasks': 5,
        'rate_limit_per_minute': 10,
        'updated_at': datetime.utcnow().isoformat() + 'Z',
        'updated_by': 'migration_script'
    }
    return config_doc

def main():
    parser = argparse.ArgumentParser(description='Migrate prompts to Firestore')
    parser.add_argument('--dry-run', action='store_true', help='Print what would be migrated without actually writing to Firestore')
    args = parser.parse_args()
    
    prompts_to_migrate = []
    
    print("🔍 Scanning for prompt files...")
    
    # Get script directory
    script_dir = Path(__file__).parent
    # Script is in backend/ folder, so script_dir IS the backend_dir
    backend_dir = script_dir
    
    # 1. Migrate single-candidate prompts
    single_prompts_dir = backend_dir / 'single-candidate-prompts'
    if single_prompts_dir.exists():
        json_files = list(single_prompts_dir.rglob('*.json'))
        print(f"   Found {len(json_files)} single-candidate prompt files")
        
        for i, filepath in enumerate(json_files, start=10):
            slug, doc = migrate_json_prompt(filepath, 'single', i)
            prompts_to_migrate.append((slug, doc))
    
    # 2. Migrate multiple-candidate prompts
    multiple_prompts_dir = backend_dir / 'multiple-candidates-prompts'
    if multiple_prompts_dir.exists():
        json_files = list(multiple_prompts_dir.glob('*.json'))
        print(f"   Found {len(json_files)} multiple-candidate prompt files")
        
        for i, filepath in enumerate(json_files, start=100):
            slug, doc = migrate_json_prompt(filepath, 'multiple', i)
            prompts_to_migrate.append((slug, doc))
    
    print(f"\n📊 Total prompts to migrate: {len(prompts_to_migrate)}")
    
    # Create webhook config
    webhook_config = create_default_webhook_config()
    
    if args.dry_run:
        print("\n🔍 DRY RUN - No data will be written to Firestore\n")
        print("=" * 80)
        print("PROMPTS COLLECTION")
        print("=" * 80)
        for slug, doc in prompts_to_migrate:
            print(f"\nDocument ID: {slug}")
            print(f"  Name: {doc['name']}")
            print(f"  Category: {doc['category']}")
            print(f"  Type: {doc['type']}")
            print(f"  Enabled: {doc['enabled']}")
            print(f"  Is Default: {doc['is_default']}")
            print(f"  Sort Order: {doc['sort_order']}")
        
        print("\n" + "=" * 80)
        print("WEBHOOK_CONFIG COLLECTION")
        print("=" * 80)
        print("\nDocument ID: default")
        for key, value in webhook_config.items():
            print(f"  {key}: {value}")
        
        print("\n✅ Dry run complete. Run without --dry-run to actually migrate.")
        return
    
    # Actually write to Firestore
    print("\n🚀 Starting migration to Firestore...")
    
    # Migrate prompts
    prompts_ref = db.collection('prompts')
    for slug, doc in prompts_to_migrate:
        prompts_ref.document(slug).set(doc)
        print(f"   ✅ Migrated: {doc['name']} ({slug})")
    
    # Create webhook config
    config_ref = db.collection('webhook_config')
    config_ref.document('default').set(webhook_config)
    print(f"   ✅ Created default webhook config")
    
    print(f"\n🎉 Migration complete!")
    print(f"   - Migrated {len(prompts_to_migrate)} prompts")
    print(f"   - Created default webhook config")
    print(f"\n🔗 View in Firestore Console:")
    print(f"   https://console.firebase.google.com/project/candidate-summary-ai/firestore/data")

if __name__ == '__main__':
    main()
