# Plan for Centralizing AI Model Configuration

Currently, AI model names are hardcoded in multiple locations across the backend. To make future updates easier and more robust, we should centralize these configurations.

## Proposed Strategy

We recommend a two-tier approach for maximum flexibility:

1.  **Environment Variables (Tier 1):** Set default model names in the `.env` file. This is standard practice and works well for stable configurations.
2.  **Firestore Settings (Tier 2):** Allow these defaults to be overridden by values stored in a Firestore collection (e.g., `settings/ai_config`). This allows for "hot-swapping" models without needing to redeploy the backend.

## Implementation Steps

### 1. Update Environment Variables
Add the following keys to `backend/.env` (and `backend/.env.example`):
```bash
# Default Gemini Models
GEMINI_MAIN_MODEL=gemini-2.0-flash
GEMINI_SUMMARY_MODEL=gemini-2.5-flash-preview-09-2025
GEMINI_QUIL_MODEL=gemini-2.0-flash-exp
```

### 2. Create a Configuration Helper
Create a new file `backend/helpers/config_helpers.py` to handle model retrieval:
```python
import os
from flask import current_app

def get_model_name(config_key, default_env_var):
    """
    Retrieves the model name from Firestore, falling back to an environment variable.
    """
    # 1. Try to get from Firestore override
    try:
        db = current_app.db
        if db:
            doc = db.collection('settings').document('ai_config').get()
            if doc.exists:
                config_data = doc.to_dict()
                if config_key in config_data:
                    return config_data[config_key]
    except Exception:
        # Fallback to env var if Firestore fails
        pass

    # 2. Fallback to Environment Variable
    return os.getenv(default_env_var)
```

### 3. Replace Hardcoded Values
Update all locations identified in `AI-MODELS.md` to use the new helper:

**Example (backend/helpers/ai_helpers.py):**
```python
from helpers.config_helpers import get_model_name

# ... inside generate_ai_response ...
model_name = get_model_name('summary_model', 'GEMINI_SUMMARY_MODEL')
response = client.models.generate_content(
    model=model_name,
    contents=prompt_parts
)
```

### 4. (Optional) Admin UI
Update the frontend to allow administrators to change these Firestore values directly through the `PromptAdmin` or a new `Settings` component.

## Benefits
- **Single Source of Truth:** Update a model name in one place.
- **No Downtime Updates:** Switch models via Firestore without restarting the server.
- **Consistency:** Ensures the same model is used for the same task across different routes.
