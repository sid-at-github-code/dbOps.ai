// Points the static frontend at the backend API.
//
// Local dev: defaults to http://localhost:8003 (start_public.py).
// Production: replace PROD_API_BASE below with your deployed backend URL
// (e.g. a Vercel deployment) before publishing this folder to Netlify.
//
// Override at runtime for testing without editing this file:
//   localStorage.setItem('API_BASE', 'https://your-backend.example.com')

const PROD_API_BASE = 'https://your-backend.vercel.app';

const API_BASE = (() => {
  const override = localStorage.getItem('API_BASE');
  if (override) return override.replace(/\/$/, '');

  const isLocal = ['localhost', '127.0.0.1'].includes(location.hostname);
  return isLocal ? 'http://localhost:8003' : PROD_API_BASE;
})();
