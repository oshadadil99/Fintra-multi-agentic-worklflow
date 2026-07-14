# Deploying Fintra to Vercel + WhatsApp Cloud API

The FastAPI app deploys to Vercel as a serverless function (`api/index.py`);
Meta's WhatsApp Cloud API delivers customer messages to `POST /webhook` and
the assistant replies through the Graph API. The sender's phone number is the
`session_id`, so conversation memory works per customer automatically.

```
WhatsApp user ──> Meta Cloud API ──> https://<app>.vercel.app/webhook
                                          │  answer_query()  (Vertex + Pinecone + Supabase)
WhatsApp user <── Meta Cloud API <── Graph API send  <──────┘
```

---

## 1. Deploy to Vercel

Prereq: the repo pushed to GitHub (or use `npx vercel` from the project root).

1. [vercel.com](https://vercel.com) → **Add New → Project** → import the GitHub repo.
   Framework preset: **Other**. No build command needed — `vercel.json`,
   `requirements.txt`, and `api/index.py` are already in place.
2. Before deploying, add the **Environment Variables** (Settings → Environment Variables):

| Variable | Value |
|---|---|
| `GOOGLE_CREDENTIALS_JSON` | paste the **entire contents** of your GCP service-account key JSON file |
| `GOOGLE_CLOUD_PROJECT` | your GCP project id |
| `GOOGLE_CLOUD_LOCATION` | `us-central1` |
| `PINECONE_API_KEY` | from the Pinecone console |
| `PINECONE_INDEX` | `fintra-kb` |
| `SUPABASE_URL` | from the Supabase dashboard |
| `SUPABASE_SERVICE_ROLE_KEY` | from the Supabase dashboard |
| `WHATSAPP_VERIFY_TOKEN` | any secret string you invent (used once in step 3) |
| `WHATSAPP_ACCESS_TOKEN` | from Meta (step 2) |
| `WHATSAPP_PHONE_NUMBER_ID` | from Meta (step 2) |

   (Model names / retrieval parameters have code defaults; override only to change them.)

3. **Deploy**, then confirm: `https://<your-app>.vercel.app/health` → `{"status":"ok"}`.

> **Size note:** the Google SDK stack is heavy. If the build exceeds Vercel's
> 250 MB function limit, the identical codebase deploys to Railway / Render /
> Cloud Run instead — only the hosting steps change.

## 2. Create the Meta WhatsApp app

1. [developers.facebook.com](https://developers.facebook.com) → **My Apps → Create App** → type **Business**.
2. In the app dashboard, **Add product → WhatsApp → Set up**. Meta gives you a
   free **test phone number** for development.
3. On **WhatsApp → API Setup**, note:
   - **Temporary access token** → `WHATSAPP_ACCESS_TOKEN` (expires in 24 h — fine
     for testing; for permanence create a System User token in Business Settings).
   - **Phone number ID** (the numeric id under the test number) → `WHATSAPP_PHONE_NUMBER_ID`.
4. Still on API Setup, **add your own WhatsApp number** to the recipient allow-list
   (test numbers can only message allow-listed recipients) and confirm the code
   Meta sends you.
5. Put both values into Vercel env vars and **redeploy** so they take effect.

## 3. Register the webhook

1. App dashboard → **WhatsApp → Configuration → Webhook → Edit**:
   - Callback URL: `https://<your-app>.vercel.app/webhook`
   - Verify token: the exact `WHATSAPP_VERIFY_TOKEN` value you set in Vercel.
2. Click **Verify and save** — Meta sends `GET /webhook` with a challenge; the
   app echoes it back if the token matches.
3. Under **Webhook fields**, subscribe to **messages**.

## 4. Test

Send *"What are your FD rates?"* from your allow-listed WhatsApp to the test
number. Expect a reply in a few seconds, grounded in the knowledge base.
Follow-ups remember context — your phone number is the session.

**Troubleshooting**
- No reply → Vercel dashboard → your project → **Logs**: every failure is logged
  with the sender id.
- `401` from Graph API in logs → the 24 h temporary token expired; refresh it.
- Webhook verification fails → `WHATSAPP_VERIFY_TOKEN` in Vercel ≠ token typed
  in the Meta console, or the env var wasn't deployed yet.
- Replies duplicated → Meta retries on slow/non-200 responses; check function
  duration in the Vercel logs (`maxDuration` is 60 s in `vercel.json`).
