# routes/admin.py - Admin routes for prompt management

from flask import Blueprint, request, jsonify, current_app
import structlog
from datetime import datetime
from google.cloud.firestore_v1.base_query import FieldFilter

log = structlog.get_logger()

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/api/admin/prompts', methods=['GET'])
def list_prompts():
    """Get all prompts (for admin UI)"""
    try:
        db = current_app.db
        # Simplified query - order by sort_order only to avoid needing composite index
        prompts_ref = db.collection('prompts').order_by('sort_order')
        docs = prompts_ref.stream()
        prompts = []
        for doc in docs:
            data = doc.to_dict()
            prompts.append({
                'id': doc.id, 'name': data.get('name'), 'slug': data.get('slug'),
                'category': data.get('category'), 'type': data.get('type'),
                'enabled': data.get('enabled'), 'is_default': data.get('is_default'),
                'sort_order': data.get('sort_order'), 'system_prompt': data.get('system_prompt'),
                'template': data.get('template'), 'user_prompt': data.get('user_prompt')
            })
        log.info("admin.list_prompts.success", count=len(prompts))
        return jsonify({'success': True, 'prompts': prompts}), 200
    except Exception as e:
        log.error("admin.list_prompts.error", error=str(e))
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/admin/prompts/<prompt_id>', methods=['GET'])
def get_prompt(prompt_id):
    try:
        db = current_app.db
        doc = db.collection('prompts').document(prompt_id).get()
        if not doc.exists:
            return jsonify({'success': False, 'error': 'Prompt not found'}), 404
        data = doc.to_dict()
        prompt = {'id': doc.id, **data}
        log.info("admin.get_prompt.success", prompt_id=prompt_id)
        return jsonify({'success': True, 'prompt': prompt}), 200
    except Exception as e:
        log.error("admin.get_prompt.error", error=str(e))
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/admin/prompts', methods=['POST'])
def create_prompt():
    try:
        db = current_app.db
        data = request.json
        required = ['name', 'slug', 'category', 'type', 'system_prompt', 'template', 'user_prompt']
        for field in required:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        slug = data['slug']
        existing = db.collection('prompts').document(slug).get()
        if existing.exists:
            return jsonify({'success': False, 'error': 'Slug already exists'}), 400
        if data.get('is_default'):
            category = data['category']
            defaults = db.collection('prompts').where(filter=FieldFilter('category', '==', category)).where(filter=FieldFilter('is_default', '==', True)).stream()
            for doc in defaults:
                doc.reference.update({'is_default': False})
        prompt_data = {
            'name': data['name'], 'slug': data['slug'], 'description': data.get('description', ''),
            'category': data['category'], 'type': data['type'], 'enabled': data.get('enabled', True),
            'is_default': data.get('is_default', False), 'sort_order': data.get('sort_order', 100),
            'system_prompt': data['system_prompt'], 'template': data['template'], 'user_prompt': data['user_prompt'],
            'created_at': datetime.utcnow().isoformat() + 'Z', 'updated_at': datetime.utcnow().isoformat() + 'Z',
            'created_by': 'admin_ui', 'updated_by': 'admin_ui'
        }
        db.collection('prompts').document(slug).set(prompt_data)
        log.info("admin.create_prompt.success", slug=slug)
        return jsonify({'success': True, 'prompt_id': slug}), 201
    except Exception as e:
        log.error("admin.create_prompt.error", error=str(e))
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/admin/prompts/<prompt_id>', methods=['PUT'])
def update_prompt(prompt_id):
    try:
        db = current_app.db
        doc_ref = db.collection('prompts').document(prompt_id)
        doc = doc_ref.get()
        if not doc.exists:
            return jsonify({'success': False, 'error': 'Prompt not found'}), 404
        data = request.json
        if data.get('is_default'):
            category = data.get('category', doc.to_dict().get('category'))
            defaults = db.collection('prompts').where(filter=FieldFilter('category', '==', category)).where(filter=FieldFilter('is_default', '==', True)).stream()
            for default_doc in defaults:
                if default_doc.id != prompt_id:
                    default_doc.reference.update({'is_default': False})
        update_data = {'updated_at': datetime.utcnow().isoformat() + 'Z', 'updated_by': 'admin_ui'}
        updatable_fields = ['name', 'slug', 'description', 'category', 'type', 'enabled', 'is_default', 'sort_order', 'system_prompt', 'template', 'user_prompt']
        for field in updatable_fields:
            if field in data:
                update_data[field] = data[field]
        doc_ref.update(update_data)
        log.info("admin.update_prompt.success", prompt_id=prompt_id)
        return jsonify({'success': True}), 200
    except Exception as e:
        log.error("admin.update_prompt.error", error=str(e))
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/admin/prompts/<prompt_id>', methods=['DELETE'])
def delete_prompt(prompt_id):
    try:
        db = current_app.db
        doc_ref = db.collection('prompts').document(prompt_id)
        doc = doc_ref.get()
        if not doc.exists:
            return jsonify({'success': False, 'error': 'Prompt not found'}), 404
        if doc.to_dict().get('is_default'):
            return jsonify({'success': False, 'error': 'Cannot delete default prompt'}), 400
        doc_ref.delete()
        log.info("admin.delete_prompt.success", prompt_id=prompt_id)
        return jsonify({'success': True}), 200
    except Exception as e:
        log.error("admin.delete_prompt.error", error=str(e))
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/admin/prompts/<prompt_id>/set-default', methods=['POST'])
def set_default_prompt(prompt_id):
    try:
        db = current_app.db
        doc_ref = db.collection('prompts').document(prompt_id)
        doc = doc_ref.get()
        if not doc.exists:
            return jsonify({'success': False, 'error': 'Prompt not found'}), 404
        data = doc.to_dict()
        category = data.get('category')
        defaults = db.collection('prompts').where(filter=FieldFilter('category', '==', category)).where(filter=FieldFilter('is_default', '==', True)).stream()
        for default_doc in defaults:
            default_doc.reference.update({'is_default': False})
        doc_ref.update({'is_default': True, 'updated_at': datetime.utcnow().isoformat() + 'Z', 'updated_by': 'admin_ui'})
        log.info("admin.set_default.success", prompt_id=prompt_id, category=category)
        return jsonify({'success': True}), 200
    except Exception as e:
        log.error("admin.set_default.error", error=str(e))
        return jsonify({'success': False, 'error': str(e)}), 500



@admin_bp.route('/api/webhook-config', methods=['GET'])
def get_webhook_config():
    """Get webhook configuration"""
    try:
        db = current_app.db
        doc = db.collection('webhook_config').document('default').get()

        if not doc.exists:
            # Return default config if not found
            default_config = {
                'enabled': True,
                'default_prompt_id': 'summary-for-platform-v2',
                'prompt_category': 'single',
                'use_quil': True,
                'use_fireflies': False,
                'proceed_without_interview': True,
                'additional_context': '',
                'auto_push': False,
                'auto_push_delay_seconds': 0,
                'create_tracking_note': False,
                'max_concurrent_tasks': 5,
                'rate_limit_per_minute': 10,
                'push_summary_to_candidate': False, # <-- ADDED
                'move_to_next_stage': False         # <-- ADDED
            }
            log.info("admin.get_webhook_config.using_defaults")
            return jsonify(default_config), 200

        data = doc.to_dict()
        log.info("admin.get_webhook_config.success")
        return jsonify(data), 200

    except Exception as e:
        log.error("admin.get_webhook_config.error", error=str(e))
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/webhook-config', methods=['PUT'])
def update_webhook_config():
    """Update webhook configuration"""
    try:
        db = current_app.db
        data = request.json

        # Validate required fields
        allowed_fields = [
            'enabled', 'default_prompt_id', 'prompt_category', 'use_quil',
            'use_fireflies', 'proceed_without_interview', 'additional_context',
            'auto_push', 'auto_push_delay_seconds', 'create_tracking_note',
            'max_concurrent_tasks', 'rate_limit_per_minute',
            'push_summary_to_candidate', # <-- ADDED
            'move_to_next_stage'         # <-- ADDED
        ]

        update_data = {}
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]

        # Add metadata
        update_data['updated_at'] = datetime.utcnow().isoformat() + 'Z'
        update_data['updated_by'] = 'admin_ui'

        # Update or create the config
        db.collection('webhook_config').document('default').set(update_data, merge=True)

        log.info("admin.update_webhook_config.success", fields=list(update_data.keys()))
        return jsonify({'success': True, 'message': 'Configuration updated'}), 200

    except Exception as e:
        log.error("admin.update_webhook_config.error", error=str(e))
        return jsonify({'error': str(e)}), 500



@admin_bp.route('/api/summary-runs', methods=['GET'])
def get_summary_runs():
    """Get summary generation runs"""
    try:
        db = current_app.db

        # Get optional query parameters
        limit_count = int(request.args.get('limit', 50))
        candidate_filter = request.args.get('candidate', '')
        job_filter = request.args.get('job', '')

        # Query Firestore
        runs_ref = db.collection('candidate_summary_runs').order_by('timestamp', direction='DESCENDING').limit(limit_count)
        docs = runs_ref.stream()

        runs = []
        for doc in docs:
            data = doc.to_dict()

            # Apply filters if provided
            if candidate_filter and candidate_filter.lower() not in (data.get('candidate_name', '') or '').lower():
                continue
            if job_filter and job_filter.lower() not in (data.get('job_name', '') or '').lower():
                continue

            # Convert timestamp to ISO string if it exists
            if 'timestamp' in data and data['timestamp']:
                data['timestamp'] = data['timestamp'].isoformat() if hasattr(data['timestamp'], 'isoformat') else str(data['timestamp'])

            runs.append({
                'id': doc.id,
                **data
            })

        log.info("admin.get_summary_runs.success", count=len(runs))
        return jsonify({'success': True, 'runs': runs}), 200

    except Exception as e:
        log.error("admin.get_summary_runs.error", error=str(e))
        return jsonify({'success': False, 'error': str(e)}), 500