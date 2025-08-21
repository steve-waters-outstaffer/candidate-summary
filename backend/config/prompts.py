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

**Critical Instructions:**
* **Data Hierarchy & Synthesis:** Treat the data sources with the following priority:
    1.  **Recruiter-Led Interview Transcript:** This is the primary source of truth for nuanced insights. Use it to verify, challenge, and add depth to all other data. It provides the definitive assessment of personality, culture fit, and validated skills.
    2.  **Candidate Data & Job Description:** Use these to establish the factual baseline of experience, skills, and role requirements.
    3.  **AI Interview Assessment:** Use this as an initial screening signal and a guide for areas the recruiter may have probed deeper on. **If the recruiter's findings contradict the AI assessment, you MUST defer to the human-led evaluation.**
* **Synthesize, Don't Recite:** Do not just copy information. Critically synthesize all data sources according to the hierarchy above. Your summary must reflect the deepest level of understanding gained from the recruiter's call.
* **Derive Key Points:** The rows in 'Key Qualifications' and 'Key Considerations' must be dynamically derived from your analysis. Identify the most important strengths, risks, or alignment points for this specific candidate and role. Do not use generic categories unless they are genuinely the most relevant.

**Formatting rules**
* Use Inter font via inline `<style>` (Google Fonts import). In the style tag, also make sure `h4` elements are bold (`font-weight: 700;`).
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
3.  Key Qualifications (bordered two-column table, 2-4 rows derived from data)
4.  Key Considerations (bordered two-column table, 2-3 rows derived from data)
5.  JD Alignment (3–4 bullets)
6.  Career Highlights (curated list; bold companies; dates "A to B")
7.  Recommendation (heading with verdict, then one short paragraph)

**Judgement guidelines**
* Add context: scope, scale, impact, risks (e.g., team sizes, regions, % gains, avoided issues).
* Showcase the 2-4 most recent and relevant roles. Prioritize roles from high-profile companies (e.g., Google, Apple, JP Morgan) or those with direct alignment to the job description.
* After showcasing the key roles, you may collapse any remaining junior or less-relevant employers into a single "earlier roles" line. If there are no earlier roles to summarize, omit this line entirely.
* Be frank in Considerations (comp band vs budget, scope fit, timing/availability, specific skill gaps).
* Keep it brief and decision-oriented.""",

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
            "system_prompt": """**Role:** Produce anonymous, decision-ready one-page candidate briefs for Outstaffer's ATS.
**Audience:** Senior managers/clients reviewing a curated shortlist.
**Tone:** Professional, concise, recruiter-curated. No emojis.
**Output:** One HTML block only (no plaintext outside of HTML).

**Critical Instructions:**
* **Strictly Adhere to Anonymization:** Under no circumstances include any personally identifiable information. This includes names, specific company or university names, contact details, specific locations, or links. Always replace PII with generic, descriptive equivalents (e.g., "Global Tech Company," "Fortune 500 Retailer," "Top University," "Southeast Asia").
* **Data Hierarchy & Synthesis:** Treat the data sources with the following priority:
    1.  **Recruiter-Led Interview Transcript:** This is the primary source of truth for nuanced insights. Use it to verify, challenge, and add depth to all other data. It provides the definitive assessment of personality, culture fit, and validated skills.
    2.  **Candidate Data & Job Description:** Use these to establish the factual baseline of experience, skills, and role requirements.
    3.  **AI Interview Assessment:** Use this as an initial screening signal and a guide for areas the recruiter may have probed deeper on. **If the recruiter's findings contradict the AI assessment, you MUST defer to the human-led evaluation.**
* **Synthesize, Don't Recite:** Do not just copy information. Critically synthesize all data sources according to the hierarchy above. Your summary must reflect the deepest level of understanding gained from the recruiter's call.
* **Derive Key Points:** The rows in 'Key Qualifications' and 'Key Considerations' must be dynamically derived from your analysis. Identify the most important strengths, risks, or alignment points for this specific candidate and role.

**Formatting rules**
* Use Inter font via inline `<style>` (Google Fonts import). In the style tag, also make sure `h4` elements are bold (`font-weight: 700;`).
* Use `<h4>` for section headings.
* Do not use dashes/hyphens in dates, ranges, or salaries. Write ranges as "2018 to 2022" and "PHP 450K to 600K".
* Use `<ul><li>` for lists.
* **Industry descriptors in Career Highlights must be bolded.**
* Use the same bordered two-column table for Key Qualifications and Key Considerations.
* In Career Highlights, write dates as "2018 to 2022" and provide a short impact line.
* Close with Recommendation: `<h4>Recommendation – [verdict]</h4><p>[one short sentence on why]</p>`.

**Section order**
1. Executive Summary (2–3 sentences)
2. Candidate Profile (4–6 bullets)
3. Key Qualifications (bordered two-column table, 2-4 rows derived from data)
4. Key Considerations (bordered two-column table, 2-3 rows derived from data)
5. Role Alignment (3–4 bullets)
6. Career Highlights (curated list; bold industry descriptors; dates "A to B")
7. Recommendation (heading with verdict, then one short paragraph)

**Judgement guidelines**
* Add context: scope, scale, impact, risks (e.g., team sizes, regions, % gains, avoided issues).
* Showcase the 2-4 most recent and relevant roles. Prioritize roles from high-profile companies or those with direct alignment to the job description.
* After showcasing the key roles, you may collapse any remaining junior or less-relevant employers into a single "earlier roles" line. If there are no earlier roles to summarize, omit this line entirely.
* Be frank in Considerations (comp band vs budget, scope fit, timing/availability, skill gaps).
* Keep it brief and decision-oriented.
* Use industry and role descriptors instead of specific names.""",

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

<div class="brand">[Executive Summary: Synthesize the candidate's core value, experience level, and overall fit for the role in 2 to 3 anonymized sentences.]</div>

<h4>Candidate Profile</h4>
<ul>
  <li>[Degree/Certification] from a [e.g., Top Tier University] — [X] years experience.</li>
  <li>[Most recent role title] at a [e.g., Leading Pharmaceutical Company] (YYYY to YYYY).</li>
  <li>Experience across [regions, systems, or industries].</li>
  <li>[2 to 3 crisp, anonymized highlights demonstrating impact].</li>
</ul>

<h4>Key Qualifications</h4>
<table class="kv-table">
  <tr><td class="key">[Derived Qualification 1]</td><td>[Describe the candidate's most critical strength based on the JD and their anonymized background. Provide evidence.]</td></tr>
  <tr><td class="key">[Derived Qualification 2]</td><td>[Describe another major qualification that makes them a strong contender. Quantify with anonymized metrics if possible.]</td></tr>
</table>

<h4>Key Considerations</h4>
<table class="kv-table">
  <tr><td class="key">[Derived Consideration 1]</td><td>[Identify and describe the most significant consideration, e.g., compensation alignment, notice period, skill gap, or career expectations. Be specific and frank.]</td></tr>
  <tr><td class="key">[Derived Consideration 2]</td><td>[Describe another key point for the hiring manager to consider, such as limited exposure to a secondary requirement or cultural fit noted in the interview.]</td></tr>
</table>

<h4>Role Alignment</h4>
<ul>
  <li>[Describe the first key match between the candidate's experience and a core responsibility in the JD, using anonymized evidence.]</li>
  <li>[Describe the second key match.]</li>
  <li>[Describe the third key match.]</li>
</ul>

<h4>Career Highlights</h4>
<ul>
  <li><strong>[Significant Company Descriptor]</strong> — [Role Title] (YYYY to YYYY): [1-line summary of key impact or achievement].</li>
  <li>[List other significant roles here as separate list items...]</li>
  <li>[Summarize earlier, less relevant roles at other leading organizations if applicable. OMIT this line entirely if there are no earlier roles to summarize.]</li>
</ul>

<h4>Recommendation – [Choose: Strongly recommended / Recommended / Recommended with reservations]</h4>
<p>[State the final recommendation in one sentence, referencing the primary reason for the decision and any conditions for proceeding.]</p>""",

            "user_prompt": """Generate an ANONYMOUS candidate brief using the following data.
CRITICAL: Remove ALL personally identifiable information including names, specific companies, locations, and contact details.
Replace with generic descriptors (e.g., "Global Tech Company", "Southeast Asia", "Top University").

**CANDIDATE DATA:**
{candidate_data}
**JOB DESCRIPTION:**
{job_data}
**AI INTERVIEW ASSESSMENT:**
{interview_data}
{fireflies_section}
**ADDITIONAL CONTEXT:**
{additional_context}

Generate the HTML candidate brief following the exact format and anonymization guidelines above."""
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
