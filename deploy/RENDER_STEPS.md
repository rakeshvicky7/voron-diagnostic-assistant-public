# Put the assistant online permanently (Render, free, basic mode, password-protected)

Hugging Face asks for a paid plan for Docker Spaces in organizations, so we use Render instead. Render builds the assistant straight from your private GitHub repository. About 15 minutes.

## 1. Push the latest files to GitHub
In the `agent` folder:
```
git add .
git commit -m "Cloud hosting: Dockerfile, password, Render steps"
git push
```

## 2. Create the web service on Render
1. Go to https://render.com and sign up with **GitHub**.
2. Click **New +** > **Web Service**.
3. Connect GitHub when asked and allow Render access to **voron-diagnostic-assistant** only.
4. Select the repository. Settings:
   - **Name:** `voron-assistant` (becomes `https://voron-assistant.onrender.com`; Render may add letters if the name is taken)
   - **Language / Runtime:** Docker (detected from the `Dockerfile`)
   - **Branch:** main
   - **Instance type:** **Free**
5. Under **Environment Variables**, add:
   - Key `DEMO_PASSWORD`, Value: a password you choose (not one you use anywhere else)
6. Click **Create Web Service**. The first build takes 5 to 10 minutes. Wait for "Live".

## 3. Test and share
1. Open the `https://....onrender.com` link. The browser asks for a user name and password: type any user name, and the password from step 2.5.
2. Test Home, Assembly (press Assemble) and Repair assistant (type a problem, open the simulation).
3. Send your professor the link and the password (preferably in two separate messages).

## Optional: connect a language model (free Groq API)
Render's free server is too small to run the model itself, so the online version can call a free cloud model instead. Your laptop version is not affected (it keeps using Ollama).
1. Create a free account at https://console.groq.com and make a **new** API key (API Keys > Create). Do not reuse keys that were ever shown in a screenshot or chat. Keep it secret.
2. In the Groq console, open **Models** and pick a model that supports **tool use**. Recommended: `openai/gpt-oss-120b` (already used with this project through Groq). Fallback: `llama-3.3-70b-versatile`. Check that the name is still listed.
3. Render dashboard > your service > **Environment** > add these variables, then **Save, rebuild and deploy**:

| Key | Value |
|---|---|
| `STUB` | `0` |
| `EMBED_STUB` | `1` |
| `PROVIDER` | `openai` |
| `OPENAI_BASE_URL` | `https://api.groq.com/openai/v1` |
| `OPENAI_API_KEY` | your Groq key |
| `LLM_MODEL` | the model name from step 2 |

4. After the deploy, the top-right label shows "Full mode". The first answer appears at once; the refined order follows after about 10 to 30 seconds.
- Accuracy with a cloud model is **not measured**: the thesis numbers are for the local qwen2.5 7B. Present it as a demo, not as the evaluated system.
- Free Groq limits (requests per minute and per day) are enough for a demo; heavy use can hit them, and then the assistant falls back to the instant answer.
- To switch the model off again, set `STUB` back to `1`.

## Make it load faster
- **Compression (built in):** the server sends the 3D model compressed (23 MB -> about 7 MB) and the browser keeps it for a week, so a second visit loads the 3D view from the browser's own cache.
- **Stop it from sleeping (free):** create a free account at https://uptimerobot.com (or https://cron-job.org), add an **HTTP monitor** for `https://YOUR-SERVICE.onrender.com/api/info`, interval **10 minutes**. The regular visit keeps the service awake, so nobody waits a minute for it to wake up. One service running all month fits in Render's free hours.
- Still slow on the very first visit: the free server is small (0.1 CPU). Open the page yourself once before a demo.

## Good to know
- **Basic mode only** (no language model): 59 % right part first, 78 % within two checks on the 69 held-out cases. Full mode on your laptop: 65 % and 91 %.
- **Sleeps after 15 minutes without visitors.** The next visit wakes it up; the first page then takes about a minute. Open it yourself shortly before a meeting.
- Visitors cannot change the saved case memory.
- **Updates:** every `git push` to main rebuilds the site automatically.
- **Change the password:** Render dashboard > your service > Environment.
- If the build fails or the page does not load, open **Logs** in the Render dashboard and send me the last lines.
