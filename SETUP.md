# Setup Guide - Candidate Summary Generator

## Prerequisites

- Node.js 18+ 
- Python 3.11+
- Firebase account (for authentication)
- Google Cloud account (for Gemini API)
- RecruitCRM API access
- AlphaRun API access

## Step-by-Step Setup

### 1. Environment Configuration

**Frontend (.env):**
```bash
cp .env.example .env
```
Edit `.env`:
```
VITE_API_URL=http://localhost:5000
```

**Backend (backend/.env):**
```bash
cd backend
cp .env.example .env
```
Edit `backend/.env`:
```
GOOGLE_API_KEY=your_google_gemini_api_key
RECRUITCRM_API_KEY=your_recruitcrm_bearer_token  
ALPHARUN_API_KEY=your_alpharun_bearer_token
FLASK_ENV=development
```

### 2. API Keys Setup

**Google Gemini API:**
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create new API key
3. Copy to `GOOGLE_API_KEY` in backend/.env

**RecruitCRM API:**
1. Login to RecruitCRM
2. Go to Settings → API Settings
3. Generate Bearer token
4. Copy to `RECRUITCRM_API_KEY` in backend/.env

**AlphaRun API:**
1. Contact AlphaRun for API access
2. Get Bearer token
3. Copy to `ALPHARUN_API_KEY` in backend/.env

### 3. Firebase Setup

1. Create Firebase project at [console.firebase.google.com](https://console.firebase.google.com)
2. Enable Authentication → Email/Password + Google
3. Copy config to `src/firebase.js`

### 4. Install Dependencies

**Frontend:**
```bash
npm install
```

**Backend:**
```bash
cd backend
pip install -r requirements.txt
```

### 5. Development

**Option 1: Use dev script (Windows):**
```bash
start-dev.bat
```

**Option 2: Manual start:**

Terminal 1 (Backend):
```bash
cd backend
python app.py
```

Terminal 2 (Frontend):
```bash
npm run dev
```

### 6. Access Application

- Frontend: http://localhost:5173
- Backend API: http://localhost:5000
- Navigate to `/summary` for the generator

## Production Deployment

### Google Cloud Run (Backend) + Firebase Hosting (Frontend)

1. **Setup gcloud CLI:**
   ```bash
   gcloud auth login
   gcloud config set project candidate-summary-ai
   ```

2. **Deploy backend to Cloud Run:**
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

3. **Setup Firebase CLI:**
   ```bash
   npm install -g firebase-tools
   firebase login
   firebase use candidate-summary-ai
   ```

4. **Update frontend env with Cloud Run URL:**
   ```
   VITE_API_URL=https://candidate-summary-api-us-central1-candidate-summary-ai.cloudfunctions.net
   ```

5. **Build and deploy frontend to Firebase:**
   ```bash
   npm run build
   firebase deploy
   ```

**Your URLs:**
- Frontend: https://candidate-summary-ai.web.app
- Backend API: https://candidate-summary-api-us-central1-candidate-summary-ai.cloudfunctions.net

## Usage

1. Login with Firebase auth
2. Navigate to Summary Generator
3. Input:
   - RecruitCRM candidate URL
   - RecruitCRM job URL
   - AlphaRun interview ID
   - Additional context (optional)
4. Generate summary
5. Review and regenerate if needed
6. Push directly to RecruitCRM

## Troubleshooting

**Backend Issues:**
- Check API keys in backend/.env
- Verify Python dependencies installed
- Check backend logs: `python app.py`

**Frontend Issues:**
- Check VITE_API_URL in .env
- Verify Firebase config in src/firebase.js
- Check browser console for errors

**API Integration:**
- Test endpoints manually with curl/Postman
- Verify URL formats match expected patterns
- Check API rate limits and permissions

## Support

For technical issues, check:
1. Browser console (F12)
2. Backend logs
3. API response status codes
4. Network tab for failed requests
