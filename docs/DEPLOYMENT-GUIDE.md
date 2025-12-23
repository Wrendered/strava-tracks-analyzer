# Foil Lab Deployment Guide

This guide covers deploying the Foil Lab platform (Backend + Frontend).

## Architecture Overview

```
┌─────────────────────┐         ┌─────────────────────┐
│   Next.js Frontend  │         │   FastAPI Backend   │
│   (foil-lab-web)    │ ──────► │ (strava-tracks-     │
│                     │  HTTPS  │      analyzer)      │
│  Platform: Vercel   │         │  Platform: Railway  │
└─────────────────────┘         └─────────────────────┘

Frontend: https://foil-lab-web.vercel.app
Backend:  https://strava-tracks-analyzer-production.up.railway.app
```

## Backend Deployment (Railway)

### Current Status
✅ **Deployed**: https://strava-tracks-analyzer-production.up.railway.app

### Setup Steps

1. **Create Railway Account**
   - Sign up at https://railway.app
   - Connect GitHub account

2. **Create New Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose `strava-tracks-analyzer` repository

3. **Configure Service**
   Railway auto-detects Python. If manual config needed:
   ```
   Build Command: pip install -r requirements.txt
   Start Command: uvicorn api.main:app --host 0.0.0.0 --port $PORT
   ```

4. **Environment Variables**
   ```bash
   # Optional - for AI gear comparison feature
   ANTHROPIC_API_KEY=your-api-key-here
   ```

5. **Deploy**
   - Railway automatically deploys on push to main
   - Monitor logs in Railway dashboard
   - Verify: `curl https://your-app.railway.app/api/health`

### Updating

Automatic deployment on push to main:
```bash
git push origin main
```

## Frontend Deployment (Vercel)

### Current Status
✅ **Deployed**: https://foil-lab-web.vercel.app

### Setup Steps

1. **Connect to Vercel**
   - Go to https://vercel.com
   - Click "Add New → Project"
   - Import `foil-lab-web` repository

2. **Configure Build Settings**
   Vercel auto-detects Next.js. Defaults work fine:
   ```
   Framework Preset: Next.js
   Build Command: npm run build
   Output Directory: .next
   ```

3. **Environment Variables**
   ```bash
   NEXT_PUBLIC_API_URL=https://strava-tracks-analyzer-production.up.railway.app
   ```

4. **Deploy**
   - Click "Deploy"
   - Wait for build (~2-3 minutes)

### Updating

Automatic deployment on push to main:
```bash
git push origin main
```

## Local Development

### Backend
```bash
cd strava-tracks-analyzer
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run_api.py
# API at http://localhost:8000
```

### Frontend
```bash
cd foil-lab-web
npm install
# Edit .env.local:
# NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
# App at http://localhost:3000
```

## Environment Configuration

### Development
```bash
# Backend - no .env needed for basic operation

# Frontend (.env.local)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Production
```bash
# Backend (Railway dashboard)
ANTHROPIC_API_KEY=sk-ant-...  # Optional

# Frontend (Vercel dashboard)
NEXT_PUBLIC_API_URL=https://strava-tracks-analyzer-production.up.railway.app
```

## Monitoring

### Railway (Backend)
- Logs: Railway Dashboard → Deployments → View Logs
- Metrics: Railway Dashboard → Metrics

### Vercel (Frontend)
- Logs: Vercel Dashboard → Deployments → Logs
- Analytics: Vercel Dashboard → Analytics

### Health Checks
```bash
# Backend
curl https://strava-tracks-analyzer-production.up.railway.app/api/health

# Should return: {"status": "healthy", "service": "foil-lab-api"}
```

## Troubleshooting

### CORS Errors
- Check allowed origins in `api/main.py`
- Verify `NEXT_PUBLIC_API_URL` in Vercel

### Build Failures
- Backend: Check Python version (3.11+ recommended)
- Frontend: Run `npm run build` locally to reproduce

### API Not Responding
- Check Railway logs for errors
- Verify the service is running in Railway dashboard
- Test health endpoint

## Cost Estimates

### Current Setup (Free/Minimal)
- Railway: Free tier or ~$5-20/month
- Vercel: Free tier (100GB bandwidth)
- **Total: $0-20/month**

### Production Setup
- Railway Pro: ~$20-50/month
- Vercel Pro: $20/month
- **Total: $40-70/month**
