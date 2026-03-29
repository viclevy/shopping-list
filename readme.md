# Family Shopping List

A real-time shared shopping list for families. Runs as a single Docker container on your home server and is accessible from any browser.

## Features

- **Real-time sync** — changes appear instantly on all connected devices via WebSocket
- **Voice input** — add, remove, or check off items using voice commands (Web Speech API)
- **Smart item setup** — new items are auto-categorized via web search; a setup dialog lets you pick a category and product image immediately after adding
- **Product catalog** — items are saved as reusable products with photos, categories, and per-store prices
- **Photo support** — search for product images, snap a photo with your camera, or upload a file
- **Store & price tracking** — track prices per store; confirm or correct at checkout
- **Analytics dashboard** — spending by week/month/year, by store, by category, most frequent items, and family member contributions
- **Multi-user** — individual accounts with activity tracking; admin manages users
- **PWA** — installable on mobile for quick home-screen access
- **Optional TLS** — serve HTTPS directly from the container with your own certificate

## Quick Start

```bash
docker build -t shopping-list .
docker run -d \
  --name shopping-list \
  -p 8080:8080 \
  -v ~/shopping-list-data:/data \
  -e ADMIN_PASSWORD=your_secret_here \
  --restart unless-stopped \
  shopping-list
```

Open `http://<your-server-ip>:8080` and log in with username **admin** and the password you set. Create accounts for family members from the admin panel.

The `-v` mount persists the database and uploaded photos across container rebuilds.

## Rebuild After Code Changes

```bash
docker stop shopping-list && docker rm shopping-list
docker build -t shopping-list .
docker run -d --name shopping-list -p 8080:8080 \
  -v ~/shopping-list-data:/data \
  -e ADMIN_PASSWORD=your_secret_here \
  --restart unless-stopped \
  shopping-list
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ADMIN_PASSWORD` | `admin` | Admin account password (set on first run) |
| `PORT` | `8080` | HTTP port |
| `DATA_DIR` | `./data` | Data directory inside the container |
| `BRAVE_SEARCH_API_KEY` | | Brave Search API key (for image search and auto-categorization) |
| `JWT_SECRET` | auto-generated | Secret for signing JWT tokens |
| `JWT_EXPIRY_HOURS` | `720` | JWT token lifetime (default 30 days) |
| `TLS_ENABLED` | `false` | Enable HTTPS |
| `TLS_CERT_FILE` | | Path to TLS certificate |
| `TLS_KEY_FILE` | | Path to TLS private key |

## Search Setup (Optional)

[Brave Search API](https://brave.com/search/api/) powers auto-categorization and product image search. Without it, these features are skipped and you can still use the app with manual entry. The free tier includes 2,000 queries/month.

1. Sign up at [brave.com/search/api](https://brave.com/search/api/)
2. Create an API key
3. Set `BRAVE_SEARCH_API_KEY` when running the container

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy, SQLite |
| Frontend | Vue 3, Vite, Pinia |
| Real-time | WebSockets (Starlette) |
| Auth | JWT with bcrypt password hashing |
| Container | Docker (single image, multi-stage build) |
| Voice | Web Speech API + Speech Synthesis (browser-native) |
| Search | Brave Search API |

## Architecture

```
Browser (desktop / mobile)
        |  HTTP + WebSocket
        v
+-------------------------------+
|  Docker Container             |
|                               |
|  FastAPI                      |
|    REST API    /api/...       |
|    WebSocket   /ws            |
|    Static SPA  /              |
|                               |
|  SQLite        /data/*.db     |
|  Uploads       /data/uploads/ |
+-------------------------------+
        |  volume mount
        v
  Host filesystem
```

## Default Stores

The app ships with these stores pre-configured. Additional stores can be added by any user.

- Stop & Shop
- Shop-Rite
- BJ's Wholesale Club
- Costco
- Whole Foods
- Trader Joe's

## License

Private project.
