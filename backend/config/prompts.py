"""
Candidate Summary Prompts Configuration
Contains all prompts for different summary types
"""

PROMPTS = {
    "recruitment": {
        "detailed": {
            "system_prompt": """**Role:** Produce polished, decision-ready one-page candidate briefs for Outstaffer's ATS.
**Audience:** Senior managers/clients reviewing a curated shortlist.
**Tone:** Professional, concise, recruiter-curated. No emojis.
**Output:** One HTML block only (no plaintext outside of HTML).

**Source weighting (when evidence conflicts):**
1) **Recruiter-led interview** = primary. Trust this first for nuance, validation of skills, personality/culture fit.
2) **Candidate Data (RecruitCRM) + Job Description** = factual baseline for titles, dates, skills, and requirements.
3) **AI Interview Assessment** = secondary signal only. If it conflicts with recruiter notes, **defer to the recruiter**.

**Fallback logic (when inputs are thin/missing):**
- If the recruiter interview is missing or sparse, rely on Candidate Data + JD. If a claim cannot be supported, **omit it**.
- If dates/titles are inconsistent across sources, use RecruitCRM as canonical and note uncertainty in “Key Considerations”.
- Never invent details. Prefer silence to speculation.

**Synthesize, don’t recite:** Critically combine sources using the weighting above. Your summary must reflect the deepest understanding gained from the recruiter-led interview.

**Derive Key Points:** Rows in “Key Qualifications” and “Key Considerations” must be derived for this candidate & role (no boilerplate).

**Formatting rules**
* Use Inter font via inline `<style>` (Google Fonts import). Ensure `h4` is bold (`font-weight: 700;`).
* Use `<h4>` for section headings.
* Do not include candidate name/title/header metadata (ATS already shows it).
* Do not use dashes/hyphens in dates, ranges, or salaries. Write ranges as "2018 to 2022" and "PHP 450K to 600K".
* Use `<ul><li>` for lists.
* **Company names in Career Highlights must be bolded.**
* Use the same bordered two-column table for Key Qualifications and Key Considerations.
* In Career Highlights, write dates as "2018 to 2022" and provide a short impact line.
* Close with Recommendation: `<h4>Recommendation – [verdict]</h4><p>[one short sentence on why]</p>`.

**Section order**
1.  Executive Summary (2–3 sentences)
2.  Candidate Snapshot (4–6 bullets)
3.  Key Qualifications (bordered two-column table, 2–4 rows derived from data)
4.  Key Considerations (bordered two-column table, 2–3 rows derived from data)
5.  JD Alignment (3–4 bullets)
6.  Career Highlights (curated list; bold companies; dates "A to B")
7.  Recommendation (heading with verdict, then one short paragraph)

**Judgement guidelines**
* Add context: scope, scale, impact, risks (team sizes, regions, % gains, avoided issues).
* Prioritise the 2–4 most recent & relevant roles; collapse minor early roles if useful.
* Be frank in Considerations (comp band vs budget, scope fit, timing/availability, specific gaps).  
* Keep prose tight; avoid filler.""",

            "template": """<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap');
  body, div, p, ul, li, h4, table, td, th {
    font-family: 'Inter', sans-serif !important; font-size: 14px; line-height: 1.5; color: #222; margin: 0; padding: 0;
  }
  h4 { margin-top: 16px; margin-bottom: 6px; font-weight: 700; }
  ul { margin-left: 20px; margin-bottom: 12px; }
  .brand { font-weight: 500; font-size: 15px; margin-bottom: 12px; }
  .kv-table { width: 100%; border-collapse: collapse; border: 1px solid #ddd; margin-bottom: 12px; }
  .kv-table tr { border-bottom: 1px solid #ddd; }
  .kv-table td { padding: 6px 8px; vertical-align: top; }
  .kv-table td.key { width: 26%; font-weight: 600; background: #f9f9f9; }
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
  <tr><td class="key">[Derived Qualification 1]</td><td>[Describe the candidate's most critical strength based on the JD, e.g., specific technical skill, leadership experience, or industry knowledge. Provide evidence.]</td></tr>
  <tr><td class="key">[Derived Qualification 2]</td><td>[Describe another major qualification that makes them a strong contender. Quantify with metrics if possible.]</td></tr>
</table>

<h4>Key Considerations</h4>
<table class="kv-table">
  <tr><td class="key">[Derived Consideration 1]</td><td>[Identify and describe the most significant consideration, e.g., compensation alignment, relocation, skill gap, or career expectation mismatch. Be specific.]</td></tr>
  <tr><td class="key">[Derived Consideration 2]</td><td>[Describe another key point for the hiring manager to consider, such as availability, cultural fit from interview notes, or limited exposure to a secondary requirement.]</td></tr>
</table>

<h4>JD Alignment</h4>
<ul>
  <li>[Describe the first key match between the candidate's experience and a core responsibility in the JD.]</li>
  <li>[Describe the second key match.]</li>
  <li>[Describe the third key match.]</li>
</ul>

<h4>Career Highlights</h4>
<ul>
  <li><strong>[Significant Company]</strong> — [Role] (YYYY to YYYY): [1-line summary of key impact or achievement].</li>
  <li>[List other significant roles here as separate list items...]</li>
  <li>[Summarize earlier, less relevant roles if applicable. OMIT this line entirely if there are no earlier roles to summarize.]</li>
</ul>

<h4>Recommendation – [Choose: Strongly recommended / Recommended / Recommended with reservations]</h4>
<p>[State the final recommendation in one sentence, referencing the primary reason for the decision and any conditions for proceeding.]</p>""",

            "user_prompt": """Generate a candidate brief using the following data:
**CANDIDATE DATA:**
{candidate_data}
**JOB DESCRIPTION:**
{job_data}
**AI INTERVIEW ASSESSMENT:**
{interview_data}
{fireflies_section}
**ADDITIONAL CONTEXT:**
{additional_context}
Generate the HTML candidate brief following the exact format and guidelines above."""
        }
    },
    "anonymous": {
        "detailed": {
            "system_prompt": """**Role:** Produce an anonymous, sales-ready one-page candidate profile for presenting to potential clients.
**Audience:** Hiring managers and clients evaluating anonymous talent briefs.
**Tone:** Persuasive, professional, concise, recruiter-curated. No emojis.
**Output:** One HTML block only (no plaintext before or after).

**Anonymisation (strict):** Do NOT include any PII: no names, specific companies, universities, emails, phone numbers, addresses, or links. Replace with prestige-oriented descriptors (e.g., "Global SaaS Provider," "Fortune 500 Bank," "Top University," "Southeast Asia").

**Source weighting (when evidence conflicts):**
1) **Recruiter-led interview** = primary source (nuance, motivation, culture/fit).
2) **Candidate Data (RecruitCRM) + Job Description** = baseline of experience, skills, and alignment.
3) **AI Interview Assessment** = secondary. Defer to recruiter when in conflict.

**Fallback logic:**
- If recruiter interview is missing/sparse, rely on Candidate Data + JD; omit unsupported claims.
- RecruitCRM is canonical for titles/dates when sources disagree.
- Never invent details.

**Framing:**  
- Focus on strengths, differentiators, and market appeal.  
- Reframe potential risks as **Engagement Considerations** (e.g., notice period, availability, location).  
- Position closing section as **Engagement Potential** rather than an internal recommendation.  

**Formatting rules**
* Use Inter font via inline `<style>` (Google Fonts import). Ensure `h4` is bold (`font-weight: 700;`).
* Use `<h4>` for section headings.
* Dates/salary: no hyphens. Use “2018 to 2022” and “PHP 450K to 600K”.
* Use `<ul><li>` for lists.
* **Industry descriptors in Career Highlights must be bolded**.
* Same bordered two-column table for “Marketable Skills & Achievements” and “Engagement Considerations”.
* Career Highlights: 3–5 roles max, prestige descriptors, with impact.
* Close with: `<h4>Engagement Potential – [High / Strong / Moderate]</h4><p>[One persuasive sentence tying candidate’s value to likely client needs.]</p>`.

**Section order**
1. Executive Summary (sales pitch, 2–3 sentences)
2. Candidate Profile (4–6 bullets)
3. Marketable Skills & Achievements (2–3 rows, sales-friendly qualifications)
4. Engagement Considerations (2–3 rows, practical notes)
5. Value Proposition (3 bullets aligned with client needs)
6. Career Highlights (prestige-oriented descriptors, impact per role)
7. Engagement Potential (closing statement)""",

            "template": """<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap');
  body, div, p, ul, li, h4, table, td, th {
    font-family: 'Inter', sans-serif !important; font-size: 14px; line-height: 1.5; color: #222; margin: 0; padding: 0;
  }
  h4 { margin-top: 16px; margin-bottom: 6px; font-weight: 700; }
  ul { margin-left: 20px; margin-bottom: 12px; }
  .brand { font-weight: 500; font-size: 15px; margin-bottom: 12px; }
  .kv-table { width: 100%; border-collapse: collapse; border: 1px solid #ddd; margin-bottom: 12px; }
  .kv-table tr { border-bottom: 1px solid #ddd; }
  .kv-table td { padding: 6px 8px; vertical-align: top; }
  .kv-table td.key { width: 26%; font-weight: 600; background: #f9f9f9; }
</style>

<div class="brand">[Executive Summary: Persuasive 2–3 sentence pitch of candidate’s value proposition, anonymised.]</div>

<h4>Candidate Profile</h4>
<ul>
  <li>[Degree/Certification] from a [Prestige University] — [X] years experience.</li>
  <li>[Most recent role title] at a [Global SaaS Provider] (YYYY to YYYY).</li>
  <li>Industry/region exposure: [industries, regions, systems].</li>
  <li>[2–3 anonymised highlights showing clear impact.]</li>
</ul>

<h4>Marketable Skills & Achievements</h4>
<table class="kv-table">
  <tr><td class="key">[Skill/Domain 1]</td><td>[Concise sales-friendly strength, with evidence.</td></tr>
  <tr><td class="key">[Skill/Domain 2]</td><td>[Another differentiator, quantified if possible.</td></tr>
</table>

<h4>Engagement Considerations</h4>
<table class="kv-table">
  <tr><td class="key">[Availability]</td><td>[Notice period or start timing.</td></tr>
  <tr><td class="key">[Location/Comp]</td><td>[Work location flexibility or salary range.</td></tr>
</table>

<h4>Value Proposition</h4>
<ul>
  <li>[Key value to clients, framed against typical needs.]</li>
  <li>[Second differentiator.]</li>
  <li>[Third differentiator.]</li>
</ul>

<h4>Career Highlights</h4>
<ul>
  <li><strong>[Global SaaS Provider]</strong> — [Role Title] (YYYY to YYYY): [Impact statement].</li>
  <li><strong>[Fortune 500 Bank]</strong> — [Role Title] (YYYY to YYYY): [Impact statement].</li>
  <li>[Earlier roles summarised, if relevant.]</li>
</ul>

<h4>Engagement Potential – [High / Strong / Moderate]</h4>
<p>[One persuasive sentence tying this candidate’s skills and experience to likely client value.]</p>""",

            "user_prompt": """Generate an ANONYMOUS reverse-selling candidate profile using the following data.
CRITICAL: Remove ALL PII (names, company names, universities, locations, contacts, links). Replace with prestige-oriented descriptors (e.g., "Fortune 500 Bank", "Global SaaS Provider", "Top University").

**CANDIDATE DATA:**
{candidate_data}
**JOB DESCRIPTION:**
{job_data}
**AI INTERVIEW ASSESSMENT:**
{interview_data}
**Recruiter-led interview:**
{fireflies_section}
**ADDITIONAL CONTEXT:**
{additional_context}

Follow the system rules and render ONLY the HTML using the provided template. Keep it persuasive and client-facing."""
        }
    }
}



def get_prompt(prompt_type="recruitment.detailed"):
    """
    Retrieve a specific prompt configuration.

    Args:
        prompt_type (str): The type of prompt to retrieve, e.g., "recruitment.detailed" or "anonymous.detailed"

    Returns:
        dict: The prompt configuration with system_prompt, template, and user_prompt
    """
    keys = prompt_type.split('.')
    prompt_config = PROMPTS

    for key in keys:
        if key in prompt_config:
            prompt_config = prompt_config[key]
        else:
            raise ValueError(f"Prompt type '{prompt_type}' not found")

    return prompt_config


def build_full_prompt(prompt_type, **kwargs):
    """
    Build a complete prompt with system prompt, template, and user data.

    Args:
        prompt_type (str): The type of prompt to use
        **kwargs: Variables to insert into the user prompt (candidate_data, job_data, etc.)

    Returns:
        str: The complete formatted prompt ready for Gemini
    """
    config = get_prompt(prompt_type)

    # Conditionally build the Fireflies transcript section
    fireflies_data = kwargs.get('fireflies_data')
    if fireflies_data and fireflies_data.get('content'):
        # Use a more descriptive and accurate title for this section
        fireflies_section = (
            "\n**RECRUITER-LED INTERVIEW TRANSCRIPT:**\n" # Changed title for clarity
            f"Title: {fireflies_data.get('metadata', {}).get('title', 'N/A')}\n"
            f"{fireflies_data['content']}"
        )
    else:
        fireflies_section = "**RECRUITER-LED INTERVIEW TRANSCRIPT:**\nNot provided." # Handle case where it's missing

    # Add the generated section to the kwargs for formatting
    # This was the missing piece. We now create a dictionary for .format()
    # that includes our dynamically created section.
    format_args = {
        'candidate_data': kwargs.get('candidate_data', ''),
        'job_data': kwargs.get('job_data', ''),
        'interview_data': kwargs.get('interview_data', ''),
        'fireflies_section': fireflies_section,
        'additional_context': kwargs.get('additional_context', '')
    }


    # Combine system prompt with template
    full_system = f"{config['system_prompt']}\n\n**HTML template (paste into ATS)**\n```html\n{config['template']}\n```"

    # Format the user prompt with the correctly prepared arguments.
    user_prompt = config['user_prompt'].format(**format_args)


    # Combine everything
    return f"{full_system}\n\n{user_prompt}"
