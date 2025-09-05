# routes/multi.py

import json
import re
from flask import Blueprint, request, jsonify, current_app
import structlog
from config.prompts import build_full_prompt
from helpers.recruitcrm_helpers import (
    fetch_recruitcrm_job,
    fetch_recruitcrm_assigned_candidates,
    fetch_recruitcrm_candidate,
    fetch_alpharun_interview,
    fetch_candidate_interview_id,
    push_to_recruitcrm_internal,
    fetch_recruitcrm_candidate_job_specific_fields
)
from helpers.ai_helpers import (
    upload_resume_to_gemini,
    generate_html_summary
)

log = structlog.get_logger()

multi_bp = Blueprint('multi_api', __name__)

@multi_bp.route('/generate-multiple-candidates', methods=['POST'])
def generate_multiple_candidates():
    """Generates content for multiple candidates."""
    data = request.get_json()
    candidate_slugs = data.get('candidate_slugs', [])
    job_slug = data.get('job_slug')
    prompt_type = data.get('prompt_type', 'candidate-submission')
    log.info("multi.generate_multiple_candidates.called", candidate_slugs=candidate_slugs, job_slug=job_slug, prompt_type=prompt_type)

    try:
        client_name = data.get('client_name', '')
        preferred_candidate = data.get('preferred_candidate', '')
        additional_context = data.get('additional_context', '')
        model = current_app.model

        if not candidate_slugs or not job_slug:
            return jsonify({'error': 'At least one candidate slug and a job slug are required'}), 400

        log.info(
            "multi.generate_multiple_candidates.processing",
            candidate_count=len(candidate_slugs),
            job_slug=job_slug,
        )

        job_data = fetch_recruitcrm_job(job_slug, include_custom_fields=True)
        if not job_data:
            return jsonify({'error': "Failed to fetch job data"}), 404

        job_details = job_data.get('data', job_data)
        job_title = job_details.get('name', '')
        alpharun_job_id = None
        for field in job_details.get('custom_fields', []):
            if isinstance(field, dict) and field.get('field_name') == 'AI Job ID':
                alpharun_job_id = field.get('value')
                break

        if not alpharun_job_id:
            log.warning(
                "multi.generate_multiple_candidates.missing_ai_job_id",
                job_slug=job_slug,
            )

        all_job_candidates = fetch_recruitcrm_assigned_candidates(job_slug)
        candidate_map = {c.get('candidate', {}).get('slug'): c.get('candidate', {}) for c in all_job_candidates}

        candidates_data = []
        failed_candidates = []
        resume_files = []

        for i, slug in enumerate(candidate_slugs):
            candidate_details = candidate_map.get(slug)
            if not candidate_details:
                log.warning(
                    "multi.generate_multiple_candidates.candidate_not_found",
                    candidate_slug=slug,
                )
                failed_candidates.append(slug)
                continue

            job_specific_fields = fetch_recruitcrm_candidate_job_specific_fields(slug, job_slug)
            if job_specific_fields:
                if 'custom_fields' in candidate_details:
                    candidate_details['custom_fields'].extend(job_specific_fields)
                else:
                    candidate_details['custom_fields'] = job_specific_fields

            gemini_resume_file = None
            resume_info = candidate_details.get('resume')
            if resume_info:
                gemini_resume_file = upload_resume_to_gemini(resume_info)
                if gemini_resume_file:
                    resume_files.append(gemini_resume_file)

            interview_data = None
            if alpharun_job_id:
                interview_id = fetch_candidate_interview_id(slug)
                if interview_id:
                    interview_data = fetch_alpharun_interview(alpharun_job_id, interview_id)
                else:
                    log.warning(
                        "multi.generate_multiple_candidates.missing_ai_interview_id",
                        candidate_slug=slug,
                    )

            candidates_data.append({
                'basic_data': {'data': candidate_details},
                'resume_file': gemini_resume_file,
                'interview_data': interview_data,
                'candidate_number': i + 1
            })

        if not candidates_data:
            return jsonify({'error': 'No valid candidate data could be retrieved'}), 400

        formatted_candidates_data = ""
        for info in candidates_data:
            details = info['basic_data']['data']
            num = info['candidate_number']
            formatted_candidates_data += f"\n**CANDIDATE {num}: {details.get('first_name')} {details.get('last_name')}**\n"
            if info['resume_file']:
                formatted_candidates_data += "Resume: Available for AI analysis\n"
            if info['interview_data']:
                formatted_candidates_data += "Interview: Completed\n"

        prompt_kwargs = {
            'client_name': client_name, 'job_url': f"https://app.recruitcrm.io/jobs/{job_slug}",
            'preferred_candidate': preferred_candidate, 'additional_context': additional_context,
            'candidates_data': formatted_candidates_data, 'job_data': job_details, 'job_title': job_title,
        }
        full_prompt = build_full_prompt(prompt_type, "multiple", **prompt_kwargs)

        prompt_contents = [full_prompt]
        if resume_files:
            prompt_contents.extend(resume_files)

        response = model.generate_content(prompt_contents)
        cleaned_content = re.sub(r'^```html\n|```$', '', response.text, flags=re.MULTILINE)
        final_content = cleaned_content.replace('[HERE_LINK]', f'<a href="https://app.recruitcrm.io/jobs/{job_slug}">here</a>')

        return jsonify({'success': True, 'generated_content': final_content}), 200

    except Exception as e:
        log.error("multi.generate_multiple_candidates.error", error=str(e))
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@multi_bp.route('/process-curated-candidates', methods=['POST'])
def process_curated_candidates():
    """Processes a curated list of candidates for a specific job."""
    data = request.get_json()
    job_slug = data.get('job_slug')
    candidate_slugs = data.get('candidate_slugs', [])
    single_prompt = data.get('single_prompt_type')
    multi_prompt = data.get('multi_prompt_type')
    auto_push = data.get('auto_push', False)
    generate_summaries = data.get('generate_summaries', False)
    generate_email = data.get('generate_email', True)
    log.info("multi.process_curated_candidates.called", job_slug=job_slug, candidate_slugs=candidate_slugs, single_prompt=single_prompt, multi_prompt=multi_prompt, auto_push=auto_push, generate_summaries=generate_summaries, generate_email=generate_email)

    model = current_app.model

    if not (generate_summaries or generate_email):
        return jsonify({'error': 'No action requested.'}), 400
    if not job_slug or not candidate_slugs:
        return jsonify({'error': 'job_slug and candidate_slugs are required.'}), 400

    processed_summaries_list = []
    failed_candidates = {}
    email_html = None

    try:
        job_data = fetch_recruitcrm_job(job_slug, include_custom_fields=True)
        if not job_data:
            return jsonify({'error': f"Could not fetch job data for slug: {job_slug}"}), 404
        job_details = job_data.get('data', job_data)

        alpharun_job_id = None
        for field in job_details.get('custom_fields', []):
            if isinstance(field, dict) and field.get('field_name') == 'AI Job ID':
                alpharun_job_id = field.get('value')
                break

        if generate_summaries or generate_email:
            for slug in candidate_slugs:
                try:
                    full_candidate_data = fetch_recruitcrm_candidate(slug)
                    if not full_candidate_data:
                        failed_candidates[slug] = "Could not fetch candidate data."
                        continue

                    job_specific_fields = fetch_recruitcrm_candidate_job_specific_fields(slug, job_slug)
                    if job_specific_fields:
                        if 'data' in full_candidate_data and 'custom_fields' in full_candidate_data['data']:
                            full_candidate_data['data']['custom_fields'].extend(job_specific_fields)
                        else:
                            full_candidate_data.setdefault('data', {})['custom_fields'] = job_specific_fields

                    candidate_details = full_candidate_data.get('data', full_candidate_data)
                    name = f"{candidate_details.get('first_name', '')} {candidate_details.get('last_name', '')}".strip()

                    gemini_resume_file = None
                    if candidate_details.get('resume'):
                        gemini_resume_file = upload_resume_to_gemini(candidate_details.get('resume'))

                    interview_data = None
                    if alpharun_job_id:
                        interview_id = fetch_candidate_interview_id(slug)
                        if interview_id:
                            interview_data = fetch_alpharun_interview(alpharun_job_id, interview_id)

                    summary = generate_html_summary(full_candidate_data, job_data, interview_data, "", single_prompt, None, gemini_resume_file, model)

                    if summary:
                        processed_summaries_list.append({'name': name, 'slug': slug, 'html': summary})
                        if auto_push and generate_summaries:
                            push_to_recruitcrm_internal(slug, summary)
                    else:
                        failed_candidates[name or slug] = "AI failed to generate summary."
                except Exception as e:
                    failed_candidates[slug] = f"An unexpected error occurred: {e}"

        if generate_email and processed_summaries_list:
            try:
                summaries_as_string = json.dumps({item['name']: item['html'] for item in processed_summaries_list}, indent=2)
                prompt_kwargs = {
                    'client_name': data.get('client_name'), 'job_url': data.get('job_url'),
                    'job_title': job_details.get('name', ''), 'job_data': job_details,
                    'processed_summaries': summaries_as_string,
                    'candidate_names': "\n".join([item['name'] for item in processed_summaries_list]),
                    'preferred_candidate': data.get('preferred_candidate'),
                    'additional_context': data.get('additional_context')
                }
                full_prompt = build_full_prompt(multi_prompt, "multiple", **prompt_kwargs)
                response = model.generate_content([full_prompt])
                if response and response.text:
                    cleaned_content = re.sub(r'^```html\n|```$', '', response.text, flags=re.MULTILINE)
                    link = data.get('job_url')
                    email_html = cleaned_content.replace('[HERE_LINK]', f'<a href="{link}">here</a>') if link else cleaned_content
            except Exception as e:
                log.error("multi.process_curated_candidates.email_generation_failed", error=str(e))

        final_response = {'success': True}
        if generate_summaries:
            final_response['summaries'] = processed_summaries_list
            final_response['failures'] = failed_candidates
        if generate_email:
            final_response['email_html'] = email_html

        return jsonify(final_response), 200

    except Exception as e:
        log.error("multi.process_curated_candidates.error", error=str(e))
        return jsonify({'error': str(e)}), 500
