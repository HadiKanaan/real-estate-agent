# AI Real Estate Agent

A two-stage LLM prompt chain system that predicts real estate prices using machine learning and explains predictions using an LLM. The user describes a property in natural language, the system extracts features, predicts the price with an ML model, and interprets the prediction in market context.

## 🎯 Quick Start

### Local Development

```powershell
# Setup environment
cp .railway.example .env
$env:GEMINI_API_KEY = "your_key_here"  # Set your Gemini API key

# Run with Docker Compose
docker-compose up

# Open browser to http://localhost:8501 (Streamlit)
# Backend runs at http://localhost:8002 (FastAPI)
```

### Railway Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete Railway setup guide.

---

## 📋 Project Structure

```
real-estate-agent/
├── app/                          # FastAPI backend
│   ├── main.py                   # FastAPI routes: /health, /extract, /predict
│   ├── llm_chain.py              # Stage 1 extraction + Stage 2 interpretation
│   ├── predictor.py              # ML prediction pipeline
│   ├── schemas.py                # Pydantic schemas (HouseFeatures, ExtractionResult, etc.)
│   ├── prompts.py                # Gemini prompts: STAGE1_PROMPT_V1, V2, STAGE2_PROMPT
│   └── model/
│       ├── pipeline.joblib       # Trained RandomForest + preprocessing
│       └── train_stats.json       # Training data statistics (for Stage 2 context)
│
├── ui/                           # Streamlit frontend
│   └── streamlit_app.py          # 6-step UI workflow
│
├── notebooks/                    # ML development & experimentation
│   └── ml_pipeline.ipynb         # EDA → training → prompt versioning
│
├── Dockerfile                    # Backend container (FastAPI)
├── Dockerfile.streamlit          # Frontend container (Streamlit)
├── docker-compose.yml            # Multi-container local setup
├── railway.toml                  # Railway.app config (auto-deployment)
├── requirements.txt              # Python dependencies
├── .env                          # (Local only) API key + URLs
├── .railway.example              # Environment template
├── DEPLOYMENT.md                 # Complete deployment guide
└── README.md                     # This file
```

---

## 🏗️ Architecture

### Two-Stage Prompt Chain

```
User Input (Natural Language)
    ↓
[STAGE 1] LLM Feature Extraction (Gemini 2.5 Flash)
    ↓ Output: Structured JSON → Pydantic HouseFeatures
    ↓
[UI Step 3] User Reviews & Fills Missing Fields
    ↓
[STAGE 2] ML Prediction (RandomForest)
    ↓ Output: Predicted price ($)
    ↓
[STAGE 3] LLM Interpretation (Gemini 2.5 Flash)
    ↓ Output: Market insight + drivers + positioning
    ↓
User Sees: Price + Interpretation + Confidence
```

### Key Components

1. **Stage 1: LLM Feature Extraction**
   - LLM parses natural language into 10 structured features
   - Returns `extracted_fields` vs. `missing_fields` for UI review
   - Two prompt variants (V1, V2); V2 chosen in notebook via testing

2. **Stage 2: ML Price Prediction**
   - Scikit-learn RandomForest (200 estimators, test R²=0.9007)
   - Trained on 1,168 samples (Ames Housing dataset)
   - 10 features: GrLivArea, BedroomAbvGr, FullBath, etc.

3. **Stage 3: LLM Interpretation**
   - Context: predicted price, median, percentiles, feature drivers
   - Returns human-readable market positioning
   - Graceful fallback if Gemini fails

---

## 📊 Bootcamp Requirements Checklist

### ML Pipeline (Notebook: `notebooks/ml_pipeline.ipynb`)

✅ **01. Split the Dataset**
- 3-way split: 1,168 train / 292 val / 731 test (no leakage)
- Cell 7

✅ **02. Handle Missing Values**
- Audited nulls on training set
- Strategies: forward-fill ordinal, mode nominal, median numeric
- Cell 7

✅ **03. Encode and Scale**
- Ordinal: OrdinalEncoder (quality scales)
- Nominal: OneHotEncoder (neighborhood, style)
- Numeric: StandardScaler
- Cell 12 (ColumnTransformer)

✅ **04. scikit-learn Pipeline**
- ColumnTransformer + Ridge, RandomForest, GradientBoosting (3 models, swappable)
- Cell 12-13

✅ **05. Compare and Report**
- Train RMSE: 5,688 | Val RMSE: 25,994 | Test RMSE: 27,491
- Test R²: 0.9007 (91% variance explained)
- Cell 14-15

### LLM Prompt Chain

✅ **06. Stage 1 — Feature Extraction**
- File: `app/llm_chain.py::stage1_extract()`
- LLM (Gemini 2.5 Flash) parses query → JSON → HouseFeatures (Pydantic)
- Completeness signal: `extracted_fields` list + `missing_fields` list
- UI shows missing fields before prediction (Step 3)

✅ **07. Stage 2 — Prediction Interpretation**
- File: `app/llm_chain.py::stage2_interpret()`
- Input: features dict + predicted price + train stats (median, p10, p90, std)
- Output: Rich text interpretation (price delta %, market positioning, feature drivers)
- Deterministic fallback if LLM fails

✅ **08. Prompt Versioning**
- File: `app/prompts.py` + notebook cells 20-21
- STAGE1_PROMPT_V1 vs. STAGE1_PROMPT_V2
- Tested on 3+ queries (notebook cell 20)
- Winner: V2 (higher extracted field count)
- Evidence logged in notebook output

✅ **09. Schemas and Error Handling**
- File: `app/schemas.py`
- HouseFeatures, ExtractionResult, PredictionRequest, AgentResponse, ErrorResponse
- Error handling:
  - JSON parse failure → empty HouseFeatures
  - API call failure → RuntimeError → Stage 2 fallback
  - Validation failure → logged + returned with confidence="low"
- Example failure case: Gemini timeout → returns deterministic market insight

### Deployment

✅ **10. FastAPI + Docker**
- File: `app/main.py` + `Dockerfile`
- Routes: `GET /health`, `POST /extract`, `POST /predict`
- Model loads at startup (no repeated loading)
- Dockerfile: python:3.11-slim, multi-layer, explicit CMD
- Build: `docker build -t real-estate-agent:v3 .`
- Run: `docker run -p 8002:8000 --env-file .env real-estate-agent:v3`
- Externally accessible ✓

✅ **11. UI**
- File: `ui/streamlit_app.py` + `Dockerfile.streamlit`
- 6-step workflow: describe → extract → review → predict → show → interpret
- Shows extracted vs. missing fields for user review
- Error handling: connection errors, malformed output, backend detection
- Text sanitization: fixes split numbers, per-character spacing, unicode

### Extra: Production Deployment

✅ **docker-compose.yml**
- Multi-container setup: backend + frontend
- Service networking, health checks, depends_on
- Local testing before Railway

✅ **railway.toml**
- Config-as-code for Railway.app
- Auto-deploys both services on git push

✅ **DEPLOYMENT.md**
- Complete guide for Railway deployment
- Environment setup, troubleshooting, monitoring

✅ **No copy-paste Dockerfiles**
- Every RUN, COPY, CMD instruction explained in comments
- Health checks, build layers, optimizations documented

---

## 🚀 Usage

### Step-by-Step (UI)

1. **Describe the House** (text input)
   - E.g., "3-bedroom ranch in a good neighborhood with a 2-car garage built in 2008"

2. **Extract Features** (LLM Stage 1)
   - System returns extracted fields + missing fields

3. **Review & Fill Missing** (manual input)
   - Override extracted values or fill in blanks
   - Only 4+ features are needed for prediction (lower confidence if fewer)

4. **Predict Price** (ML model)
   - RandomForest predicts based on final feature set
   - Shows confidence level

5. **See Price** (output)
   - Predicted price displayed with ±

6. **See Interpretation** (LLM Stage 2)
   - Market context: price delta vs. median, feature drivers, market positioning
   - If Gemini unavailable: deterministic fallback (always returns useful text)

### API Endpoints

**Backend at `http://localhost:8002` (or Railway URL)**

#### `POST /extract`
```json
{
  "query": "3 bed ranch with garage built in 2008"
}
```
Response:
```json
{
  "features": {
    "GrLivArea": 1500,
    "BedroomAbvGr": 3,
    "FullBath": 1,
    ...
  },
  "extracted_fields": ["GrLivArea", "BedroomAbvGr", "FullBath"],
  "missing_fields": ["HalfBath", "OverallQual", ...],
  "confidence": "medium",
  "needs_clarification": true
}
```

#### `POST /predict`
```json
{
  "query": "...",
  "features": {
    "GrLivArea": 1500,
    "BedroomAbvGr": 3,
    ...
  }
}
```
Response:
```json
{
  "predicted_price": 185000.0,
  "interpretation": "The predicted price is $185,000, which is above the training median...",
  "extracted_fields": [...],
  "missing_fields": [...],
  "confidence": "high",
  "warning": null
}
```

#### `GET /health`
Response: `{"status": "ok"}`

---

## 🛠️ Development

### Adding a Feature

1. Update `app/schemas.py` → `HouseFeatures`
2. Update `notebooks/ml_pipeline.ipynb` → retrain
3. Serialize new model: `joblib.dump(pipeline, "app/model/pipeline.joblib")`
4. Update `app/prompts.py` → Stage 1 & 2 prompts mention new feature
5. Rebuild: `docker build -t real-estate-agent:v4 .`

### Tweaking Prompts

1. Edit `app/prompts.py` (STAGE1_PROMPT_V2 or STAGE2_PROMPT)
2. Test locally: `python -c "from app.llm_chain import stage1_extract; print(stage1_extract('your query'))"`
3. Or create new version: STAGE1_PROMPT_V3, test in notebook cell 20
4. Update `app/llm_chain.py` to use new version
5. Rebuild + push

### Running Locally Without Docker

```powershell
# Setup
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Backend
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
streamlit run ui\streamlit_app.py
```

---

## 📦 Deployment Options

### Option 1: Railway.app (Recommended for Bootcamp)
- Auto-deploys on git push
- Environment variables via UI
- Docker Compose compatible
- See [DEPLOYMENT.md](DEPLOYMENT.md)

### Option 2: Docker Compose (Local Testing)
```powershell
docker-compose up
# Backend: http://localhost:8002
# Frontend: http://localhost:8501
```

### Option 3: Heroku (Legacy)
```powershell
git push heroku main
# Requires Procfile (not included)
```

### Option 4: Self-Hosted (AWS, GCP, etc.)
Use docker-compose.yml or Kubernetes manifests (not included)

---

## 📈 Model Metrics

| Metric | Train | Validation | Test |
|--------|-------|-----------|------|
| RMSE | $5,688 | $25,994 | $27,491 |
| R² | 0.9945 | 0.9009 | 0.9007 |
| MAE | $3,221 | $17,814 | $18,932 |

**Best Model:** RandomForest (200 estimators)

---

## 🔑 Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `GEMINI_API_KEY` | Google Gemini API key (REQUIRED) | `AIz...` |
| `API_URL` | Backend URL (Streamlit only) | `http://localhost:8002` |
| `PORT` | FastAPI port (Railway sets) | `8000` |

Never commit `.env` with real keys. Use `.railway.example` as template.

---

## 🐛 Troubleshooting

**"Could not reach backend" in Streamlit**
- Verify backend is running: `docker ps` or Railway dashboard
- Check API_URL is correct
- Ensure both services are in same docker network (docker-compose handles this)

**"GEMINI_API_KEY is missing"**
- Set env var: `$env:GEMINI_API_KEY = "..."`
- Or add to .env file
- Regenerate key at https://aistudio.google.com/app/apikeys

**"Module not found" error**
- Rebuild image: `docker build -t real-estate-agent .`
- Verify requirements.txt is current

**Slow first prediction**
- Model loads on first request; cache persists
- Subsequent predictions are ~100ms

---

## 📚 References

- **Bootcamp:** AI Program Week 2 (LLM + ML + Deployment)
- **Dataset:** Ames Housing (Kaggle)
- **LLM:** Google Gemini 2.5 Flash
- **ML:** Scikit-learn RandomForest
- **UI:** Streamlit
- **Backend:** FastAPI + Uvicorn
- **Deploy:** Railway.app + Docker

---

## ✅ Checklist Before Submission

- [ ] Notebook runs end-to-end (all cells executed)
- [ ] Model metrics saved: test RMSE, R², best model name
- [ ] Prompt versions tested (V1 vs. V2) with evidence in notebook
- [ ] FastAPI routes tested with real Gemini API
- [ ] Streamlit UI runs without errors (6 steps)
- [ ] Docker images build without errors
- [ ] docker-compose.yml works locally (both services)
- [ ] railway.toml present (config-as-code)
- [ ] .gitignore excludes .env and model artifacts
- [ ] DEPLOYMENT.md covers Railway setup
- [ ] GitHub repo is public and pushed
- [ ] All code commented and explained
- [ ] No vibe coding; every line understood

---

## 📝 Submission Details

Hadi Kanaan | Dataset: Ames Housing (Kaggle) | Best model: RandomForest | Test RMSE: 27,491
LLM: Gemini 2.5 Flash | Prompt versions: 2 | Docker image: real-estate-agent:v3 | Notebook: https://github.com/HadiKanaan/real-estate-agent/blob/main/notebooks/ml_pipeline.ipynb | Repo: https://github.com/HadiKanaan/real-estate-agent

---

## 👤 License

Free to use for educational purposes (AIE Program).

---

## 📞 Questions?

See comments in code, docstrings, and DEPLOYMENT.md for detailed explanations.
