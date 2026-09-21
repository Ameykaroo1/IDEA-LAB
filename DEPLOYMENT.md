# CRYSTAL-X Cloud Deployment Guide

This guide details how to deploy CRYSTAL-X to free cloud hosting using **Vercel** for the frontend and **Render** (or **Railway**) for the scientific backend.

---

## Architecture Overview

```
[ User Browser ]
       │
       ▼
[ Vercel (Next.js 14 Frontend) ]
  • Minimalist scientific UI
  • Interactive 3D WebGL crystal viewer
  • Transparent proxy to backend via /api/:path*
       │
       ▼ (HTTPS)
[ Render / Railway (FastAPI Backend) ]
  • Deterministic pymatgen validation
  • Material requirement extraction & normalization
  • StructureMatcher deduplication against MP-20 / JARVIS-DFT
  • Downstream DFT input generation
```

---

## Step 1: Push Your Code to GitHub

Your local repository is already initialized and committed. Run the following in your terminal:

```bash
# 1. Create a new repository on GitHub (e.g. named 'crystal-x')
# 2. Link your local repository to GitHub:
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/crystal-x.git
git branch -M main
git push -u origin main
```

---

## Step 2: Deploy the Backend to Render (Free)

1. Log into [dashboard.render.com](https://dashboard.render.com).
2. Click **New +** $\to$ **Web Service**.
3. Connect your GitHub repository (`crystal-x`).
4. Configure the service:
   - **Name**: `crystal-x-backend`
   - **Region**: Oregon (US West) or Frankfurt (EU)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`
5. Click **Create Web Service**.
6. Copy your public backend URL once deployed (e.g., `https://crystal-x-backend.onrender.com`).

> **Tip (Alternative 1-Click Blueprint)**:  
> You can also click **New +** $\to$ **Blueprint** on Render and select your repository. Render will automatically read `render.yaml` to deploy both services together.

---

## Step 3: Deploy the Frontend to Vercel (Free)

1. Log into [vercel.com](https://vercel.com).
2. Click **Add New...** $\to$ **Project**.
3. Import your `crystal-x` GitHub repository.
4. In the project configuration:
   - **Root Directory**: Click *Edit* and select `frontend`.
   - **Framework Preset**: `Next.js` (automatically detected).
5. Open the **Environment Variables** section and add:
   - **Key**: `BACKEND_URL`
   - **Value**: `https://crystal-x-backend.onrender.com` (your Render backend URL from Step 2)
   - *(Optional)* **Key**: `NEXT_PUBLIC_API_URL`
   - *(Optional)* **Value**: `https://crystal-x-backend.onrender.com/api`
6. Click **Deploy**.

Within 1–2 minutes, Vercel will give you a live production URL (e.g., `https://crystal-x.vercel.app`).

---

## Verification Checklist

Once both services are deployed:
- [ ] Open `https://your-frontend.vercel.app` and confirm the rotating 3D $\text{LiCoO}_2$ crystal renders smoothly on the landing page.
- [ ] Navigate to `/discover` and verify the status badge reads `DEMO_GENERATOR ACTIVE` or `MATTERGEN CONNECTED`.
- [ ] Click **"Extract Requirements"** and run a discovery test to ensure API communication is active.
- [ ] Visit `/candidates` and test the 3D unit cell inspector and CIF file download.
