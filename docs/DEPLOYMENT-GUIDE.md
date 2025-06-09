# Foil Lab Deployment Guide

This guide covers deploying all components of the Foil Lab platform.

## Architecture Overview

```
┌─────────────────────┐         ┌─────────────────────┐
│   Streamlit App     │         │   Next.js Frontend  │
│  (Traditional UI)   │         │   (Modern UI)       │
│                     │         │                     │
│  Platform: TBD      │         │  Platform: Vercel   │
│  URL: TBD           │         │  URL: foil-lab.app  │
└─────────────────────┘         └──────────┬──────────┘
                                           │
                                           │ HTTPS
                                           ▼
                                ┌─────────────────────┐
                                │   FastAPI Backend   │
                                │                     │
                                │  Platform: Railway  │
                                │  URL: *.railway.app │
                                └─────────────────────┘
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
   ```yaml
   # Railway configuration
   Build Command: pip install -r requirements.txt
   Start Command: uvicorn api.main:app --host 0.0.0.0 --port $PORT
   Root Directory: /strava-tracks-analyzer
   ```

4. **Environment Variables**
   ```bash
   # Required
   ANTHROPIC_API_KEY=your-api-key-here  # For AI features
   
   # Optional
   PORT=8000                            # Railway provides this
   ```

5. **Deploy**
   - Railway automatically deploys on push to main
   - Monitor logs in Railway dashboard
   - Check health: `GET /api/health`

### Updating

```bash
# Automatic deployment on push
git push origin main

# Manual redeploy in Railway dashboard
# Settings → Redeploy
```

## Frontend Deployment (Vercel)

### Prerequisites
- GitHub repository created for `foil-lab-web`
- Vercel account (free tier is sufficient)

### Setup Steps

1. **Create GitHub Repository**
   ```bash
   # In foil-lab-web directory
   gh repo create foil-lab-web --public
   git push -u origin feature/initial-ui
   ```

2. **Connect to Vercel**
   - Go to https://vercel.com
   - Click "Add New → Project"
   - Import `foil-lab-web` repository
   - Select `feature/initial-ui` branch

3. **Configure Build Settings**
   ```yaml
   Framework Preset: Next.js
   Root Directory: ./
   Build Command: npm run build
   Output Directory: .next
   Install Command: npm install
   ```

4. **Environment Variables**
   ```bash
   NEXT_PUBLIC_API_URL=https://strava-tracks-analyzer-production.up.railway.app
   ```

5. **Deploy**
   - Click "Deploy"
   - Wait for build completion (~2-3 minutes)
   - Access at provided URL

### Custom Domain (Optional)
1. In Vercel dashboard → Settings → Domains
2. Add custom domain (e.g., foil-lab.app)
3. Update DNS records as instructed

### Updating

```bash
# Automatic deployment
git push origin main

# Preview deployments for PRs
git push origin feature/new-feature
# Creates preview at: https://foil-lab-git-feature-new-feature.vercel.app
```

## Streamlit Deployment Options

### Option 1: Streamlit Community Cloud (Recommended)

1. **Sign Up**
   - Go to https://streamlit.io/cloud
   - Sign in with GitHub

2. **Deploy App**
   - Click "New app"
   - Select repository: `strava-tracks-analyzer`
   - Main file path: `strava-tracks-analyzer/app.py`
   - Python version: 3.11

3. **Secrets Management**
   ```toml
   # In Streamlit Cloud settings
   [secrets]
   ANTHROPIC_API_KEY = "your-api-key-here"
   ```

### Option 2: Railway (Alternative)

Similar to API deployment but with different start command:
```yaml
Start Command: streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

### Option 3: Docker (Self-Hosted)

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

## Environment Configuration

### Development
```bash
# Backend (.env)
ANTHROPIC_API_KEY=sk-ant-...
DEBUG=true

# Frontend (.env.local)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Production
```bash
# Backend (Railway)
ANTHROPIC_API_KEY=sk-ant-...
CORS_ORIGINS=https://foil-lab.vercel.app,https://foil-lab.app

# Frontend (Vercel)
NEXT_PUBLIC_API_URL=https://strava-tracks-analyzer-production.up.railway.app
```

## Monitoring & Logs

### Railway (Backend)
- Logs: Railway Dashboard → Deployments → View Logs
- Metrics: Railway Dashboard → Metrics
- Alerts: Configure in Railway settings

### Vercel (Frontend)
- Logs: Vercel Dashboard → Functions → Logs
- Analytics: Vercel Dashboard → Analytics
- Speed Insights: Automatically enabled

### Health Checks
```bash
# Backend health
curl https://your-api.railway.app/api/health

# Frontend health (Next.js)
curl https://your-app.vercel.app/api/health  # If implemented
```

## Security Considerations

### API Security
1. **CORS Configuration**
   ```python
   # Restrict in production
   origins = [
       "https://foil-lab.vercel.app",
       "https://foil-lab.app",
       "https://your-streamlit-app.streamlit.app"
   ]
   ```

2. **Rate Limiting** (Future)
   ```python
   from slowapi import Limiter
   limiter = Limiter(key_func=get_remote_address)
   ```

3. **API Keys** (Future)
   - Implement API key authentication
   - Rate limit by API key
   - Monitor usage

### Frontend Security
1. **Environment Variables**
   - Never commit `.env.local`
   - Use `NEXT_PUBLIC_` prefix for client-side vars
   - Keep sensitive data server-side only

2. **Content Security Policy**
   ```javascript
   // next.config.js
   const securityHeaders = [
     {
       key: 'Content-Security-Policy',
       value: "default-src 'self'; ..."
     }
   ]
   ```

## Performance Optimization

### Backend
1. **Caching** (Future)
   - Redis for analysis results
   - Cache repeated calculations
   - TTL based on file hash

2. **Async Processing** (Future)
   - Celery for long-running tasks
   - WebSocket for real-time updates

### Frontend
1. **Image Optimization**
   - Next.js Image component
   - Lazy loading
   - WebP format

2. **Code Splitting**
   - Dynamic imports for heavy components
   - Route-based splitting automatic

## Backup & Recovery

### Database (Future)
- Daily automated backups
- Point-in-time recovery
- Test restore procedures

### File Storage (Future)
- S3 or similar for GPX files
- Versioning enabled
- Lifecycle policies

## Scaling Considerations

### Horizontal Scaling
- Railway: Increase replicas
- Vercel: Automatic scaling
- Load balancer for multiple backends

### Vertical Scaling
- Railway: Upgrade instance size
- Monitor memory usage
- Optimize algorithms for large files

## Troubleshooting

### Common Issues

1. **CORS Errors**
   - Check allowed origins in backend
   - Verify API URL in frontend
   - Clear browser cache

2. **Build Failures**
   - Check logs for specific errors
   - Verify all dependencies installed
   - Ensure correct Python/Node versions

3. **Performance Issues**
   - Monitor API response times
   - Check for memory leaks
   - Optimize database queries

### Debug Commands
```bash
# Test API locally
curl -X POST http://localhost:8000/api/analyze-track \
  -F "file=@test.gpx" \
  -F "wind_direction=270"

# Check Next.js build
npm run build
npm run start

# Streamlit debug mode
streamlit run app.py --logger.level=debug
```

## Cost Estimates

### Current Setup (Minimal)
- Railway: ~$5-20/month (usage-based)
- Vercel: Free tier (100GB bandwidth)
- Total: ~$5-20/month

### Production Setup (Recommended)
- Railway: ~$20-50/month (dedicated resources)
- Vercel Pro: $20/month (more bandwidth)
- Monitoring: ~$10/month
- Total: ~$50-80/month

### Enterprise Setup
- Multiple Railway instances: ~$100-200/month
- Vercel Enterprise: Custom pricing
- CDN, monitoring, backups: ~$100-200/month
- Total: ~$300-500/month

## Maintenance

### Regular Tasks
- [ ] Weekly: Check logs for errors
- [ ] Monthly: Update dependencies
- [ ] Quarterly: Security audit
- [ ] Yearly: Major version upgrades

### Update Procedures
```bash
# Backend updates
pip install --upgrade -r requirements.txt
git add requirements.txt
git commit -m "Update dependencies"
git push origin main

# Frontend updates
npm update
npm audit fix
git add package*.json
git commit -m "Update dependencies"
git push origin main
```

## Support Contacts

- Railway Support: https://railway.app/help
- Vercel Support: https://vercel.com/support
- Streamlit Support: https://discuss.streamlit.io/