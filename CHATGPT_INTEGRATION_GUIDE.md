# How to Connect ChatGPT to CRYSTAL-X

There are **two ways** to allow ChatGPT to access your CRYSTAL-X platform:

---

## Method 1: Direct Web Browsing (ChatGPT with Web Access)

You can ask ChatGPT (or any web-enabled AI model) to browse and analyze your running website directly.

### 1. Live Public URLs (Active Now)
- **Frontend Website**: [`https://ready-otters-refuse.loca.lt`](https://ready-otters-refuse.loca.lt)
- **Backend API**: [`https://yellow-clubs-burn.loca.lt`](https://yellow-clubs-burn.loca.lt)
- **API Documentation**: [`https://yellow-clubs-burn.loca.lt/docs`](https://yellow-clubs-burn.loca.lt/docs)

> [!NOTE]
> **Localtunnel Password (if prompted in browser)**:
> Localtunnel displays an anti-phishing splash screen on first visit.
> - **Tunnel Password / IP**: `47.11.12.62`
> Enter this number and click "Click to Continue" to unlock access.

### Example Prompt to ChatGPT:
```
Please visit https://ready-otters-refuse.loca.lt and review the CRYSTAL-X Material Discovery platform.
Examine the Discovery Studio, the natural language requirement extraction workflow, and the candidate library.
```

---

## Method 2: ChatGPT Custom GPT "Action" (Recommended)

You can create a specialized **Custom GPT** in ChatGPT that can directly call your CRYSTAL-X backend to discover, validate, screen, and rank crystal materials directly in chat conversations.

### Step-by-Step Setup:
1. Open [ChatGPT](https://chat.openai.com/) and go to **Explore GPTs** $\to$ **Create a GPT** (or Edit an existing GPT).
2. Under the **Configure** tab:
   - **Name**: `CRYSTAL-X Assistant`
   - **Description**: `AI-powered crystal material discovery and crystallographic screening engine.`
   - **Instructions**:
     ```
     You are the CRYSTAL-X Material Discovery Assistant. You help computational materials scientists discover and screen inorganic crystals for advanced energy storage (batteries, solid electrolytes).
     When the user describes a target material:
     1. Use the parseRequirements action to extract required elements, excluded elements, target band gaps, and stability preferences.
     2. Ask the user for confirmation.
     3. Call runDiscovery to generate candidates and perform crystallographic validation with pymatgen.
     4. Present the ranked candidates with their validation statuses and property predictions.
     5. Always maintain scientific honesty: remind the user that ML predictions and demo candidates require downstream DFT and experimental validation.
     ```
3. Scroll down to **Actions** and click **Create new action**.
4. In the **Schema** box, copy and paste the contents of:
   [`exports/chatgpt_action_schema.json`](file:///c:/Users/Amey/OneDrive/Desktop/iiidea/exports/chatgpt_action_schema.json)
   *(Or click "Import from URL" and enter: `https://yellow-clubs-burn.loca.lt/openapi.json`)*.
5. Set **Authentication** to: `None`.
6. Click **Save / Update** in the top right.

### Example Chat with Your Custom GPT:
> *"I need a silicon-based material for energy storage with a band gap around 2.3 eV and no toxic elements like lead or mercury. Discover candidate crystals for me."*

ChatGPT will call your local CRYSTAL-X backend via the live tunnel, run pymatgen validation, and return ranked crystal candidates directly into your chat!

---

## Method 3: Alternative Tunnels (ngrok or Cloudflare)

If you prefer a tunnel without the localtunnel password prompt:

### Option A: ngrok
```powershell
# 1. Sign up at ngrok.com (free) and get your auth token
ngrok config add-authtoken YOUR_TOKEN

# 2. Expose the frontend
ngrok http 3000

# 3. Expose the backend
ngrok http 8000
```

### Option B: Cloudflare Quick Tunnels (Zero configuration)
```powershell
# Download cloudflared from https://github.com/cloudflare/cloudflared/releases
cloudflared tunnel --url http://localhost:3000
```
This gives an instant, password-less `*.trycloudflare.com` public HTTPS address that ChatGPT can access directly.
