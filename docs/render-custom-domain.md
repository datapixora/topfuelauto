# Render custom domain setup

## Steps in Render (Web service)
1) Open Render Dashboard ? Services ? `topfuelauto-web` ? Settings ? Custom Domains.
2) Click “Add Custom Domain” and enter both `topfuelauto.com` and `www.topfuelauto.com`.
3) Render will show the DNS targets (CNAME/ALIAS). Copy them for registrar configuration.
4) Wait for DNS propagation; Render will provision SSL automatically once records resolve.
5) (Optional) Set one domain as primary and enable redirect (www -> apex or vice versa) in Render’s domain settings.

## Steps at your domain registrar (DNS)
- Create the DNS records exactly as Render instructs. Do not invent values.
- Typical pattern:
  - For `www`: CNAME pointing to the Render-provided target.
  - For apex (`topfuelauto.com`): ALIAS/ANAME/flattened CNAME to the Render-provided target (or A/AAAA if Render gives IPs).
- Save and allow time to propagate.

## Application configuration after DNS is live
- Web service env var: `NEXT_PUBLIC_API_BASE_URL=https://api.topfuelauto.com/api/v1` (adjust to your API domain).
- API service env var: `ALLOWED_ORIGINS=https://topfuelauto.com,https://www.topfuelauto.com,https://topfuelauto-web.onrender.com,http://localhost:3000`.
- Redeploy both services so CORS and frontend point to the correct domains.

## Redirect www -> apex (optional)
- Prefer configuring in Render custom domain settings (set primary and enable redirect).
- If needed at app level, add a lightweight Next.js middleware to redirect `www.` to apex.

## Verify
1) Visit https://topfuelauto.com and ensure the web UI loads.
2) Check the home “Service status” card; it should call the API and show JSON from `/health`.
3) Confirm SSL padlock on both apex and www.