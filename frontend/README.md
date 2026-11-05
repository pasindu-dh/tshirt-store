# FURZY frontend

React 19 + Vite storefront and admin UI for the FURZY T-Shirt Store API.

## Local development

```bash
npm install
npm run dev
```

The API defaults to `http://127.0.0.1:8005`. Set `VITE_API_URL` in a local
`.env` file to use another backend:

```bash
VITE_API_URL=http://127.0.0.1:8005
```

## Checks

```bash
npm test
npm run lint
npm run build
```

## Vercel deployment

- Root directory: `frontend`
- Framework: Vite
- Install: `npm ci --include=dev`
- Build: `npm run build`
- Output: `dist`
- Node.js: 22.12 or newer

Set `VITE_API_URL` in the Vercel project environment to the public Render API
URL, for example `https://furzy-api.onrender.com`. Use a full `https://` URL
with no trailing slash. Vite embeds this value at build time, so redeploy after
changing it. The build fails if the variable is missing or not HTTPS.

Vercel Hobby is free for non-commercial personal/university projects; this
demo configuration targets that plan.

`vercel.json` rewrites SPA routes to `index.html`, adds security headers, and
caches hashed assets. After the Vercel domain is known, add the exact origin
to the backend `FRONTEND_ORIGINS`; preview deployments need their own exact
origins because wildcard CORS is rejected in production.
