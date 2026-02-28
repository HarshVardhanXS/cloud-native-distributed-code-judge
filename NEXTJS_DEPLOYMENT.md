# Next.js Deployment Guide

## Local Development

### 1. Setup `.env.local`

```bash
# Copy example file
cp .env.local.example .env.local
```

### 2. Environment Variables

Edit `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_DEBUG=false
```

**Important:** Variables prefixed with `NEXT_PUBLIC_` are exposed to the browser and build output.

### 3. Run Locally

```bash
npm install
npm run dev
```

Visit `http://localhost:3000`

---

## Vercel Deployment

### 1. Connect Repository

- Push code to GitHub
- Go to [vercel.com](https://vercel.com)
- Click "New Project"
- Import GitHub repository
- Framework preset: **Next.js**

### 2. Set Environment Variables

In Vercel Dashboard:

1. Select your project
2. Go to **Settings → Environment Variables**
3. Add variables for **Production**, **Preview**, and **Development**:

#### Production (e.g., deployed app)
```
NEXT_PUBLIC_API_URL=https://your-api-domain.com
NEXT_PUBLIC_DEBUG=false
```

#### Preview (e.g., staging branches)
```
NEXT_PUBLIC_API_URL=https://staging-api.com
NEXT_PUBLIC_DEBUG=false
```

#### Development (local)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_DEBUG=true
```

### 3. Deploy

- Click **Deploy** button
- Vercel automatically builds and deploys on every push to `main`
- View production URL in Vercel dashboard

---

## Environment Variable Hierarchy

| Environment | `.env.local` | Vercel Dashboard | Priority |
|---|---|---|---|
| `npm run dev` | ✅ Used | ❌ Ignored | `.env.local` wins |
| `npm run build` (local) | ✅ Used | ❌ Ignored | `.env.local` wins |
| Vercel Deployment | ❌ Not used | ✅ Used | Dashboard wins |

**Note:** `.env.local` is in `.gitignore` and never committed to Git.

---

## Troubleshooting

### API Connection Issues

**Local:** Ensure FastAPI runs on `http://localhost:8000`

**Vercel:** Update `NEXT_PUBLIC_API_URL` to your deployed API domain (e.g., `https://api.example.com`)

### CORS Errors

The FastAPI backend must allow your frontend domain in `CORS_ORIGINS`:

**Local:**
```
CORS_ORIGINS=http://localhost:3000
```

**Vercel:**
```
CORS_ORIGINS=https://your-vercel-domain.vercel.app,https://your-custom-domain.com
```

---

## Quick Commands

```bash
# Local development
npm run dev

# Build for production
npm run build

# Test production build locally
npm run build && npm run start

# View environment variables being used
npm run build -- -d
```

---

## Deployment Checklist

- [ ] `.env.local` created from `.env.local.example`
- [ ] `NEXT_PUBLIC_API_URL` points to FastAPI backend
- [ ] Repository pushed to GitHub
- [ ] Vercel project created and connected
- [ ] Environment variables set in Vercel dashboard
- [ ] FastAPI `CORS_ORIGINS` includes Vercel domain
- [ ] Test deployment URL works
