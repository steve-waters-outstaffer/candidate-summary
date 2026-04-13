# routes/floating.py
# Floating (anonymous) candidate summary - candidate-only workflow, no job required.

import structlog
from flask import Blueprint, request, jsonify, current_app, Response

log = structlog.get_logger()
log.info("routes.floating: Top of file, starting imports.")

try:
    from helpers.recruitcrm_helpers import fetch_recruitcrm_candidate, fetch_candidate_notes, parse_alpharun_interview_from_notes
    from helpers.ai_helpers import upload_resume_to_gemini, generate_floating_html_summary
    from helpers.pdf_helpers import generate_pdf_from_html
    log.info("routes.floating: All imports successful.")
except Exception as e:
    log.error("routes.floating.import_failed", error=str(e), exc_info=True)
    import sys
    sys.exit(1)

floating_bp = Blueprint('floating_api', __name__)


@floating_bp.route('/floating/test-candidate', methods=['POST'])
def floating_test_candidate():
    """Validates a candidate slug and returns the candidate's name."""
    log.info("floating.test_candidate.hit")
    data = request.get_json()
    slug = data.get('candidate_slug')
    if not slug:
        return jsonify({'error': 'Missing candidate_slug'}), 400

    response_data = fetch_recruitcrm_candidate(slug)
    if response_data:
        candidate_details = response_data.get('data', response_data)
        name = f"{candidate_details.get('first_name', '')} {candidate_details.get('last_name', '')}".strip()
        return jsonify({
            'success': True,
            'message': 'Candidate confirmed',
            'candidate_name': name
        })
    return jsonify({'error': 'Failed to fetch candidate data'}), 404


@floating_bp.route('/floating/test-resume', methods=['POST'])
def floating_test_resume():
    """Checks whether the candidate has a resume on file."""
    log.info("floating.test_resume.hit")
    data = request.get_json()
    candidate_slug = data.get('candidate_slug')
    if not candidate_slug:
        return jsonify({'error': 'Missing candidate_slug'}), 400

    candidate_data = fetch_recruitcrm_candidate(candidate_slug)
    if candidate_data:
        candidate_details = candidate_data.get('data', candidate_data)
        resume_info = candidate_details.get('resume')
        if resume_info and (resume_info.get('url') or resume_info.get('file_link')):
            return jsonify({
                'success': True,
                'message': 'Resume found',
                'filename': resume_info.get('filename', 'Resume on file')
            })
        return jsonify({'success': False, 'message': 'No resume on file'})
    return jsonify({'error': 'Failed to fetch candidate data'}), 404


@floating_bp.route('/floating/test-interview', methods=['POST'])
def floating_test_interview():
    """Checks whether the candidate has an AI Interview Note on file."""
    log.info("floating.test_interview.hit")
    data = request.get_json()
    candidate_slug = data.get('candidate_slug')
    if not candidate_slug:
        return jsonify({'error': 'Missing candidate_slug'}), 400

    notes = fetch_candidate_notes(candidate_slug)
    interview_content = parse_alpharun_interview_from_notes(notes)

    if interview_content:
        # Extract job opening name from first line if present
        first_line = interview_content.split('\n')[0]
        label = first_line.replace('Job Opening:', '').strip()[:60] if 'Job Opening:' in first_line else 'Interview found'
        return jsonify({'success': True, 'message': label})

    return jsonify({'success': False, 'message': 'No AI interview note found'})


@floating_bp.route('/floating/generate-summary', methods=['POST'])
def floating_generate_summary():
    """Generates an anonymous floating candidate summary HTML."""
    log.info("floating.generate_summary.hit")
    data = request.get_json()
    candidate_slug = data.get('candidate_slug')
    additional_context = data.get('additional_context', '')
    prompt_type = data.get('prompt_type', 'floating.candidate-v1')
    client = current_app.client

    if not candidate_slug:
        return jsonify({'error': 'Missing candidate_slug'}), 400

    candidate_data = fetch_recruitcrm_candidate(candidate_slug)
    if not candidate_data:
        return jsonify({'error': 'Failed to fetch candidate data'}), 500

    candidate_details = candidate_data.get('data', candidate_data)
    resume_info = candidate_details.get('resume')
    gemini_resume_file = upload_resume_to_gemini(resume_info, client) if resume_info else None

    # Fetch AI interview from candidate notes (no job context needed)
    candidate_notes = fetch_candidate_notes(candidate_slug)
    alpharun_interview = parse_alpharun_interview_from_notes(candidate_notes)
    log.info("floating.generate_summary.interview_source",
             candidate_slug=candidate_slug,
             has_alpharun_interview=bool(alpharun_interview))

    html_summary = generate_floating_html_summary(
        candidate_data=candidate_data,
        additional_context=additional_context,
        prompt_type=prompt_type,
        gemini_resume_file=gemini_resume_file,
        client=client,
        alpharun_interview=alpharun_interview
    )

    if html_summary:
        log.info("floating.generate_summary.success", candidate_slug=candidate_slug)
        return jsonify({'success': True, 'html_summary': html_summary})

    return jsonify({'error': 'AI generation failed'}), 500


@floating_bp.route('/floating/generate-pdf', methods=['POST'])
def floating_generate_pdf():
    """Converts the generated HTML summary to a downloadable PDF."""
    log.info("floating.generate_pdf.hit")
    data = request.get_json()
    html_summary = data.get('html_summary')
    candidate_name = data.get('candidate_name', 'Candidate')

    if not html_summary:
        return jsonify({'error': 'Missing html_summary'}), 400

    pdf_bytes, filename = generate_pdf_from_html(html_summary, candidate_name, 'Floating-Summary')

    if not pdf_bytes:
        return jsonify({'error': 'PDF generation failed'}), 500

    return Response(
        pdf_bytes,
        mimetype='application/pdf',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Length': str(len(pdf_bytes))
        }
    )
