# Deployment Guide: AI Real Estate Agent

## Overview

The AI Real Estate Agent is a two-stage LLM prompt chain system that extracts house features from natural language and predicts prices using a trained ML model. This guide covers deploying the complete application (backend + frontend) to **Railway.app**.

---

## Project Architecture

```
┌─────────────────────────────────────────────────────────┐
│              User Browser (Streamlit UI)                │
│  - Step 1: Describe house in natural language           │
│  - Step 2: Extract features (Stage 1 LLM)               │
│  - Step 3: Review/fill missing fields                   │
│  - Step 4: Predict price (ML model)                     │
│  - Step 5: Show prediction                              │
│  - Step 6: Interpret (Stage 2 LLM)                      │
└─────────────────────────────────────────────────────────┘
                     ↓ HTTP/REST ↑
┌─────────────────────────────────────────────────────────┐
│              FastAPI Backend (Docker)                    │
│  - POST /extract: Stage 1 LLM feature extraction         │
│  - POST /predict: Full chain (extract → predict → interp)│
│  - GET /health: Health check                            │
│                                                          │
│  Components:                                             │
│  - LLM Chain: Google Gemini 2.5 Flash                    │
│  - ML Pipeline: Scikit-learn RandomForest               │
│  - Feature Engineering: ColumnTransformer (ordinal,      │
│                         nominal, numeric)               │
│  - Model Artifacts: pipeline.joblib, train_stats.json   │
└─────────────────────────────────────────────────────────┘
```

---

## Prerequisites

1. **Production Requirements:**
   - Railway.app account (https://railway.app)
   - GitHub repository with this project
   - Google Gemini API key: https://aistudio.google.com/app/apikeys

2. **Local Development (Optional):**
   - Docker & Docker Compose
   - Python 3.11+
   - pip or uv package manager

---

## Local Testing with Docker Compose

Before deploying to Railway, test the complete stack locally:

### 1. Prepare Environment

```powershell
# Copy the example environment file
cp .railway.example .env

# Edit .env and add your real GEMINI_API_KEY
# (or export it from your shell)
$env:GEMINI_API_KEY = "your_actual_key_here"
```

### 2. Build and Run Services

```powershell
# Build both images
docker-compose build

# Start backend and frontend
docker-compose up

# Backend will be at: http://localhost:8002
# Frontend will be at: http://localhost:8501
```

### 3. Test the Workflow

1. Open browser to `http://localhost:8501`
2. Verify sidebar shows "Current backend: http://backend:8000" (inter-container name)
3. Run a test query through all 6 steps
4. Verify price prediction and interpretation display correctly

### 4. Checking Logs

```powershell
# View backend logs
docker-compose logs -f backend

# View frontend logs
docker-compose logs -f frontend

# Stop services
docker-compose down
```

---

## Deployment to Railway

### Method 1: Using Railway CLI (Recommended)

#### 1. Install Railway CLI

```powershell
# Using npm
npm i -g @railway/cli

# Or download from https://railway.app/cli
```

#### 2. Create Railway Project

```powershell
# Login to Railway
railway login

# Initialize project in repo directory
railway init

# Select "Real Estate Agent" as project name or use Railway UI
```

#### 3. Configure Services

In Railway dashboard (https://railway.app/dashboard):

1. **Create Backend Service:**
   - Source: Connect GitHub repo
   - Dockerfile: `Dockerfile`
   - Port: 8000
   - Environment:
     - `GEMINI_API_KEY`: (paste your actual key)

2. **Create Frontend Service:**
   - Source: Same GitHub repo
   - Dockerfile: `Dockerfile.streamlit`
   - Port: 8501
   - Environment:
     - `GEMINI_API_KEY`: (same key)
     - `API_URL`: `https://<backend-railway-url>/` (set after backend deploys)

#### 4. Deploy

```powershell
# Deploy from CLI
railway up

# Or deploy via Railway dashboard by pushing to GitHub
git push origin main
```

#### 5. Verify Deployment

- Backend health: `https://<backend-url>/health` → should return `{"status":"ok"}`
- Frontend: `https://<frontend-url>` → Streamlit UI should load

---

### Method 2: Using railway.toml (Config as Code)

The `railway.toml` file defines both services. Railway automatically detects and deploys both services when you push to GitHub.

**Advantages:**
- Version control for deployment config
- Reproducible deployments
- Easy service linking

**Usage:**
```powershell
# Push to GitHub (ensure .env is in .gitignore, NOT committed)
git push origin main

# Railway detects railway.toml and auto-deploys both services
# Monitor progress in Railway dashboard
```

---

### Method 3: Using Docker Hub (For Custom Deployments)

If you want to host on your own infrastructure:

```powershell
# Build images
docker build -t your-registry/real-estate-agent:backend -f Dockerfile .
docker build -t your-registry/real-estate-agent:frontend -f Dockerfile.streamlit .

# Push to registry
docker push your-registry/real-estate-agent:backend
docker push your-registry/real-estate-agent:frontend

# Deploy using docker-compose on your server
docker-compose -f docker-compose.yml up -d
```

---

## Environment Variables Reference

### Backend (FastAPI)

| Variable | Purpose | Example |
|----------|---------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | `AIza...` |
| `PORT` | FastAPI port (Railway sets this) | `8000` |
| `LOG_LEVEL` | Logging verbosity | `info`, `debug` |

### Frontend (Streamlit)

| Variable | Purpose | Example |
|----------|---------|---------|
| `API_URL` | Backend endpoint | `https://backend.railway.app` |
| `RAILROAD_BACKEND_URL` | Set by Railway (override manually if needed) | Auto-set |
| `GEMINI_API_KEY` | (Optional) For local Streamlit dev | `AIza...` |
| `STREAMLIT_SERVER_HEADLESS` | Run in headless mode | `true` |
| `STREAMLIT_SERVER_PORT` | Port Streamlit runs on | `8501` |
| `STREAMLIT_SERVER_ADDRESS` | Bind address | `0.0.0.0` |

---

## Architecture Decisions & Trade-offs

### Why Two Containers?

1. **Separation of Concerns:**
   - Backend handles ML + LLM logic (heavier, longer compute)
   - Frontend handles UI only (lightweight, fast reload)

2. **Independent Scaling:**
   - Front-end UI can be scaled separately
   - Backend can have more resources (1GB+ RAM for model)

3. **Technology Fit:**
   - FastAPI + uvicorn: perfect for REST API + async
   - Streamlit: perfect for interactive UI with minimal code

### Model in Container

The trained model (`app/model/pipeline.joblib`, ~200MB) is **baked into the Docker image**:
- ✅ One-step deployment (no external artifact storage)
- ✅ Model version matches code version
- ❌ Slightly larger image (~1.5 GB total)
- ❌ To update model, rebuild + redeploy

To use external artifact storage (S3, GCS) instead:
```python
# In app/predictor.py, instead of loading from disk:
# import boto3
# s3 = boto3.client('s3')
# s3.download_file('bucket', 'pipeline.joblib', '/tmp/pipeline.joblib')
```

### Service Discovery

- **Local (docker-compose):** `http://backend:8000` (hostname)
- **Railway:** `https://<backend-service-url>.railway.app` (HTTPS required)
- **Custom link:** Set `API_URL` in frontend environment

---

## Troubleshooting

### Frontend Can't Reach Backend

**Symptom:** "Could not reach backend health endpoint" warning

**Solution:**
1. Check `API_URL` in Railway environment variables
2. Verify backend service is running (green status in Railway dashboard)
3. Ensure backend URL has protocol (`https://`, not just domain)
4. Check CORS settings (add to FastAPI if needed):
   ```python
   from fastapi.middleware.cors import CORSMiddleware
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

### Gemini API Key Not Working

**Symptom:** "GEMINI_API_KEY is missing" error

**Solution:**
1. Verify key is set in Railway environment variables (not committed to Git)
2. Regenerate key at https://aistudio.google.com/app/apikeys
3. Check key is valid (copy-paste, no extra spaces)
4. Ensure API is enabled in Google Cloud project

### Streamlit Crashes on Startup

**Symptom:** Container exits immediately or "module not found"

**Solution:**
1. Check logs: `railway logs <service-name>`
2. Verify `requirements.txt` has all dependencies
3. Ensure `Dockerfile.streamlit` copies `ui/streamlit_app.py`
4. Rebuild and redeploy:
   ```powershell
   git push origin main
   # Railway rebuilds automatically
   ```

### Model Takes Too Long to Load

**Symptom:** "timeout waiting for service to start"

**Symptom:** First request hangs

**Solution:**
1. Increase Railway service startup timeout in dashboard
2. Load model on startup in `app/main.py` (already done):
   ```python
   from app.predictor import predict  # triggers model load
   ```
3. Use larger Railway plan with more RAM if model won't fit

---

## Monitoring & Maintenance

### Health Checks

Both services have built-in health checks:

```powershell
# Backend health
curl https://<backend-url>/health
# Expected: {"status":"ok"}

# Frontend health
curl https://<frontend-url>/_stcore/health
# Expected: Streamlit health status JSON
```

### Logs

View logs in Railway dashboard:
1. Go to project → select service
2. Click "Deployment" tab
3. Expand deployment row → "View logs"

### Updates

To update code:
```powershell
git push origin main
# Railway auto-rebuilds and redeploys both services
```

To update dependencies:
1. Modify `requirements.txt`
2. Push to GitHub
3. Railway rebuilds with new dependencies

---

## Bootcamp Rubric Compliance

✅ **01. Split the Dataset:** 3-way split (train/val/test) with no leakage. See `notebooks/ml_pipeline.ipynb` cell 7.

✅ **02. Handle Missing Values:** Audited on training set; strategies chosen per feature type. Cell 7.

✅ **03. Encode and Scale:** ColumnTransformer distinguishes ordinal/nominal/numeric. Cell 12.

✅ **04. scikit-learn Pipeline:** ColumnTransformer + Ridge, RandomForest, GradientBoosting (swappable). Cell 12-13.

✅ **05. Compare and Report:** Train vs. validation vs. test scores. Cell 14-15.

✅ **06. Stage 1 — Feature Extraction:**
   - LLM (Gemini) parses query into typed HouseFeatures (Pydantic)
   - Completeness signal: `extracted_fields` vs. `missing_fields`
   - UI shows what's missing before prediction

✅ **07. Stage 2 — Prediction Interpretation:**
   - Feed Stage 2 features + prediction + train stats (median, p10, p90, std)
   - Returns rich interpretation (vs. raw number)
   - Fallback: deterministic market insight on API error

✅ **08. Prompt Versioning:**
   - STAGE1_PROMPT_V1 and STAGE1_PROMPT_V2 in notebook
   - Tested on 3+ queries; V2 winner logged
   - Evidence: extracted field count, JSON parse success

✅ **09. Schemas and Error Handling:**
   - HouseFeatures, ExtractionResult, PredictionRequest, AgentResponse schemas
   - Catches JSON errors, API errors, validation failures
   - Fallback: empty features → missing all fields OR deterministic market insight

✅ **10. FastAPI + Docker:**
   - FastAPI app with POST /extract and /predict
   - Dockerfile builds image with model + dependencies
   - Port mapped, externally accessible

✅ **11. UI:**
   - Streamlit with 6-step workflow
   - Shows extracted vs. missing; user fills gaps
   - Displays prediction + interpretation
   - Error handling + backend detection

---

## Next Steps

1. **Local Testing:** Run `docker-compose up` and test all 6 steps
2. **Railway Setup:** Create project at Railway.app and link GitHub
3. **Set Environment Variables:** Add `GEMINI_API_KEY` in Railway UI
4. **Deploy:** Push to GitHub (Railway auto-deploys)
5. **Verify:** Open Streamlit URL and run a prediction
6. **Monitor:** Check logs in Railway dashboard for issues

---

## Additional Resources

- [Railway.app Docs](https://docs.railway.app)
- [Streamlit Deployment](https://docs.streamlit.io/deploy)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices)

---

## Support

For issues:
1. Check logs in Railway dashboard
2. Test locally with `docker-compose up`
3. Verify environment variables
4. Ensure GEMINI_API_KEY is valid
5. Check GitHub commit has all required files
