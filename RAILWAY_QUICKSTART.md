# Railway Deployment Quickstart

**Goal:** Deploy backend + frontend to Railway in 10 minutes.

---

## Prerequisites

1. **Railway.app account**: Free tier works fine
2. **GitHub**:  Public repo with this project pushed
3. **Google Gemini API key**: https://aistudio.google.com/app/apikeys

---

## Step 1: Push to GitHub

```powershell
# Ensure .env is in .gitignore (do NOT commit secrets)
git status
# Should NOT show .env in staged files

# Push code
git push origin main
```

---

## Step 2: Create Railway Project

1. Go to https://railway.app/dashboard
2. Click **"New Project"**
3. Select **"Deploy from GitHub"**
4. Authorize GitHub + select this repo
5. Click **"Deploy"**

Railway auto-detects `railway.toml` and creates both services (backend + frontend).

---

## Step 3: Configure Environment Variables

In Railway dashboard:

1. **Go to Backend Service** → Variables tab
2. Add: `GEMINI_API_KEY` = `AIza...` (your actual key)
3. **Go to Frontend Service** → Variables tab
4. Add: 
   - `GEMINI_API_KEY` = (same key)
   - `API_URL` = (leave empty, will auto-fill with backend URL)

---

## Step 4: Wait for Deployment

Railway rebuilds from `Dockerfile` and `Dockerfile.streamlit`.

- **Backend** deploys to: `https://<project>-backend.railway.app`
- **Frontend** deploys to: `https://<project>-frontend.railway.app`

Check "Deployment" tab for status. Green = ✅ running.

---

## Step 5: Test

1. Open **Frontend URL** in browser
2. Verify sidebar shows backend URL
3. Run test query through all 6 steps
4. See price prediction + interpretation

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Frontend can't reach backend | Check backend URL in Railway is https (not http) |
| "GEMINI_API_KEY is missing" | Add to both service variables (yes, both) |
| Container crashes on startup | Check logs in Railway Deployment tab |
| Model takes 30+ seconds to load | First request is slow; container is starting |

---

## Cost

Railway free tier includes:
- Up to 500 build minutes/month
- $5/month usage credit (usually enough for small projects)

See [railway.app/pricing](https://railway.app/pricing)

---

## Next Steps After Deployment

1. **Monitor**: Check Railway logs if issues arise
2. **Update code**: Push to GitHub → Railway auto-redeploys
3. **Scale**: Use Railway dashboard to add more resources if needed

---

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed troubleshooting and architecture info.
