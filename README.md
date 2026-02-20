> **This project is intended for research and educational purposes only.**
> Please use it responsibly and refrain from any commercial use.

# WebAI-to-API

A FastAPI server that exposes Google Gemini (via browser cookies) as a local OpenAI-compatible API endpoint. No API key required — it reuses your existing browser session.

Compatible with any tool that supports the OpenAI API format: [Open WebUI](https://github.com/open-webui/open-webui), [Cursor](https://cursor.sh), [Continue](https://continue.dev), custom scripts, etc.

---

## Deployment with Docker Compose

### 1. Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with Docker Compose v2

### 2. Clone the repository

```bash
git clone https://github.com/leolionart/WebAI-to-API.git
cd WebAI-to-API
```

### 3. Get your Gemini cookies

1. Open [gemini.google.com](https://gemini.google.com) and log in
2. Open DevTools (`F12`) → **Application** → **Cookies** → `https://gemini.google.com`
3. Copy the values of `__Secure-1PSID` and `__Secure-1PSIDTS`

### 4. Create and configure `config.conf`

```bash
cp config.conf.example config.conf
```

Open `config.conf` and paste your cookies:

```ini
[Cookies]
gemini_cookie_1psid   = paste __Secure-1PSID value here
gemini_cookie_1psidts = paste __Secure-1PSIDTS value here
```

Other settings you may want to change:

```ini
[AI]
default_model_gemini = gemini-2.5-flash   # model to use by default

[Proxy]
http_proxy =   # optional, e.g. http://127.0.0.1:7890 if Gemini is blocked
```

### 5. Start the server

```bash
docker compose up -d
```

The API is now running at **`http://localhost:6969`**.

Cookies are stored in a Docker named volume and survive restarts. The server also auto-rotates `__Secure-1PSIDTS` in the background — no manual cookie refresh needed.

---

## Verify it's working

```bash
curl http://localhost:6969/v1/models
```

Expected response:

```json
{
  "object": "list",
  "data": [
    { "id": "gemini-3.0-pro", ... },
    { "id": "gemini-2.5-pro", ... },
    { "id": "gemini-2.5-flash", ... }
  ]
}
```

---

## Making API requests

The server exposes an OpenAI-compatible endpoint at `/v1/chat/completions`.

### Supported models

| Model | Description |
|-------|-------------|
| `gemini-3.0-pro` | Most capable |
| `gemini-2.5-pro` | Advanced reasoning |
| `gemini-2.5-flash` | Fast, efficient (default) |

### Example: curl

```bash
curl http://localhost:6969/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-flash",
    "messages": [{ "role": "user", "content": "Hello!" }]
  }'
```

### Example: OpenAI Python client

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:6969/v1",
    api_key="not-needed",
)

response = client.chat.completions.create(
    model="gemini-2.5-flash",
    messages=[{"role": "user", "content": "Hello!"}],
)
print(response.choices[0].message.content)
```

### Example: with system prompt and conversation history

```json
{
  "model": "gemini-2.5-pro",
  "messages": [
    { "role": "system", "content": "You are a helpful assistant." },
    { "role": "user", "content": "What is Python?" },
    { "role": "assistant", "content": "Python is a programming language." },
    { "role": "user", "content": "Is it easy to learn?" }
  ]
}
```

---

## All endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/models` | List available models |
| `POST` | `/v1/chat/completions` | OpenAI-compatible chat |
| `POST` | `/gemini` | Stateless single-turn request |
| `POST` | `/gemini-chat` | Stateful multi-turn chat |
| `POST` | `/translate` | Translation (same as `/gemini-chat`) |
| `POST` | `/v1beta/models/{model}:generateContent` | Google Generative AI format |

Swagger UI available at `http://localhost:6969/docs`.

---

## Common operations

```bash
# View logs
docker compose logs -f

# Stop
docker compose down

# Update to latest image
docker compose pull && docker compose up -d

# Restart
docker compose restart
```

---

## Updating cookies

If your session expires, paste new cookie values into `config.conf` and restart:

```bash
docker compose restart
```

The volume keeps your config between restarts — you only need to re-edit the file.

---

## Configuration reference

Full `config.conf` options:

```ini
[Browser]
# Browser for automatic cookie extraction (if cookies are left empty above).
# Options: chrome, firefox, brave, edge, safari
name = chrome

[AI]
default_ai = gemini
default_model_gemini = gemini-2.5-flash

[Cookies]
gemini_cookie_1psid   =
gemini_cookie_1psidts =

[EnabledAI]
gemini = true

[Proxy]
# Optional HTTP proxy for Gemini connections (useful for 403 errors).
http_proxy =
```

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Amm1rr/WebAI-to-API&type=Date)](https://www.star-history.com/#Amm1rr/WebAI-to-API&Date)

## License

[MIT License](LICENSE)
