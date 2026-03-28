# Family Shared Shopping List

A shared, real-time shopping list application for families — accessible from any web browser on desktop or mobile,
running entirely on a home server via Docker.

---

## Overview

The goal is to replace the current Home Assistant todo workaround with a purpose-built shared shopping list that supports:

- Voice-driven item entry (button-triggered, with quantity/unit support)
- Photos attached to items (multiple per item, auto-resized)
- Per-store price tracking (with optional confirmation at checkout)
- Real-time sync across all family members' devices
- Individual user accounts with activity tracking
- Automatic history and repeat-purchase suggestions
- Analytics dashboard on spending and purchase frequency

---

## Core Features

### Data Model

The data is split across three tables with distinct responsibilities:

#### Products (catalog)

Stable reference data for known products. Reused across shopping list entries and purchases.

| Field | Required | Notes |
|---|---|---|
| Name | Yes | Searchable, plain text |
| Photo(s) | Suggested | One or more snapshots of the product (e.g. front and back) |
| Stores | Suggested | One or more stores where this product is available |
| Price (per store) | Suggested | Estimated via web search or last-known; updated when confirmed at checkout |
| Category | Suggested | e.g. Produce, Dairy, Frozen — suggested via web search, user can override |

Suggested means an online search can suggest a value but suggestion should favor values from history if available.

A product record is created once and reused every time the same item is added to the list. Photos, category,
store availability, and prices are maintained on the product and shared across all list entries.

#### Shopping List (active items)

Items currently needed. Each entry references a product.

| Field | Required | Notes |
|---|---|---|
| Product | Yes | Reference to a Products record |
| Quantity | Yes | Defaults to 1 if not specified |
| Unit | No | e.g. gallons, lbs, oz — omitted for countable items |
| Added by | Auto | Which family member added it |
| Added at | Auto | Timestamp |

When an item is checked off or removed, its Shopping List entry is deleted (the event is recorded in History).

#### History (event log)

Every action on the shopping list is recorded as an event.

| Field | Required | Notes |
|---|---|---|
| Product | Yes | Reference to a Products record |
| Action | Yes | One of: added, modified, checked_off, removed |
| User | Auto | Which family member performed the action |
| Timestamp | Auto | When the action occurred |
| Store | No | Store where the item was purchased (check-off events only) |
| Price | No | Confirmed price at time of purchase (check-off events only) |
| Quantity | No | Quantity at time of action |
| Unit | No | Unit at time of action |
| Details | No | Additional context (e.g. what was modified, reason for removal) |

This table powers the analytics dashboard, repeat-purchase suggestions, price history, and full audit trail.

### Shopping List

- Any family member can add, edit, or remove items
- Adding an item creates a Shopping List entry referencing a Product; if the product doesn't exist yet, a new
  Product record is created automatically
- **Check off** = item was purchased. The Shopping List entry is removed and a `checked_off` event is recorded
  in History with who bought it, when, at which store, and the confirmed price. The Product's stored price is
  updated if the user corrected it.
- **Remove** = item is no longer needed (e.g. changed mind, duplicate). The Shopping List entry is removed and
  a `removed` event is recorded in History. Not counted as a purchase in analytics.
- The list syncs in real time across all open sessions (no manual refresh needed), this can be kept in the backend and simply require online connectivity instead of pulling data to endge devices and keeping them up to date.

### Voice Input

- Voice recognition — no extra hardware or accounts required - a button one can click to add/remove or check something off the list
- Supported commands:
  - **Add:** "add milk", "add two gallons of whole milk"
  - **Remove:** "remove milk", "remove whole milk"
  - **Check off:** "check off milk", "bought milk"
- Supports quantities and units; defaults to quantity 1 when not specified
- The app announces a confirmation via text-to-speech after each voice command is processed
  (TTS only activates when voice input is being used, not for manual UI actions)
- Works on both desktop (Chrome/Edge) and mobile browsers

### Item Search and History

- When adding a new item, the input searches the Products catalog for existing products
- Selecting an existing product pre-fills name, photo, stores, and last-known price from the Product record
- If no match is found, a new Product record is created and suggestions are fetched via Google Custom Search API
- Prevents duplicate product records and speeds up re-ordering regular groceries

### Photo Attachment

- Search for the full product name (e.g. "Lactaid Lactose Free Fat Milk") via Google Custom Search API and extract
  images from the results using regex scraping; let the user select the best matching picture
- Alternatively, allow the user to take a photo directly from the phone camera or upload an image file
- Each item can have multiple photos (e.g. front and back of packaging)
- Photos are automatically resized to JPEG format (max 2 MB) on upload
- Photos are stored on the server and displayed as thumbnails on the list

### Store and Price Tracking

- Each item can be associated with one or more of the supported stores
- Prices are suggested by searching the full product name via Google Custom Search API and extracting prices
  from results using regex scraping; falls back to manual entry when no price is found
- When checking off an item, users can optionally select which store they are buying from; the selection is
  cached per session so they don't have to re-select for every item while shopping at the same store
- Users are optionally prompted to confirm or correct the suggested price at check-off
- Over time this builds a price history used in analytics

### Analytics

Tracked data enables reports such as:

- Total spending per week / month / year
- Spending breakdown by store
- Spending breakdown by category
- Most frequently purchased items
- Purchase frequency per item (useful for auto-suggesting when to re-add)
- Contribution by family member (who adds and who buys most)

---

## Technology Stack

### Deployment

- Single Docker container running on the home server
- Exposed on a local network port (e.g. `http://homeserver:8080`)
- TLS served directly by FastAPI using a provided SSL certificate (optional, enabled via config)
- Runs plain HTTP by default for local development; TLS enabled for external access
- **Configuration:** environment variables for single values (e.g. `ADMIN_PASSWORD`, `PORT`, `TLS_ENABLED`);
  file path references for structured credentials (e.g. `GOOGLE_CREDENTIALS_FILE` pointing to a JSON key file)

### Backend

| Concern | Candidate |
|---|---|
| Language / framework | Python + FastAPI |
| Database | SQLite (simplest, no extra container) |
| Real-time sync | WebSockets (FastAPI native via Starlette) |
| File storage | Local filesystem volume mounted into the container |
| Auth | Per-user accounts with passwords (admin creates users) |

### External Services

| Service | Purpose |
|---|---|
| Google Custom Search API | Category suggestions, price and image extraction via regex scraping of search results; falls back to manual entry when results are insufficient |
| Web Speech API (browser) | Voice input (runs client-side, no server API needed) |
| Speech Synthesis API (browser) | Text-to-speech confirmations for voice commands (client-side) |

### Frontend

- Single-page application (SPA) served by the same container
- **Vue 3** with **Vite** build tooling
- Responsive design — works on small phone screens and large desktop monitors
- Installable as a **Progressive Web App (PWA)**: adds to home screen for quick access

### Why Not Extend Home Assistant?

HASS custom integrations and Lovelace cards are viable but come with trade-offs:

| Approach | Pros | Cons |
|---|---|---|
| Standalone app | Full control, simpler data model, easier to develop and maintain | Separate URL, separate login from HASS |
| HASS integration | Re-uses HASS mobile app (GPS already works), single app for family | Tightly coupled to HASS internals, HASS updates can break custom code, limited UI flexibility |

**Recommended starting point:** standalone web app as a PWA. HASS integration can be added later
as a one-way sync (e.g. HASS triggers add items via a webhook) if the voice assistant or mobile
app integration is desired.

---

## Architecture Sketch

```
Browser (desktop / mobile)
        │  HTTP + WebSocket
        ▼
┌───────────────────────────────┐
│  Docker Container             │
│                               │
│  ┌──────────────────────────┐ │
│  │  Web Server              │ │
│  │  (FastAPI)               │ │
│  │                          │ │
│  │  REST API  /api/...      │ │
│  │  WebSocket /ws           │ │
│  │  Static files  /         │ │
│  └──────────┬───────────────┘ │
│             │                 │
│  ┌──────────▼───────────────┐ │
│  │  Database (SQLite)       │ │
│  └──────────────────────────┘ │
│                               │
│  ┌──────────────────────────┐ │
│  │  File Storage            │ │
│  │  /data/uploads/          │ │
│  └──────────────────────────┘ │
└───────────────────────────────┘
        │  volume mount
        ▼
  Host filesystem  ~/shopping-list-data/
```

---

## Design Decisions

### Authentication & Identity

- **Individual user accounts:** Each family member has their own account to track who added, removed, or checked off items.
  This enables the analytics contribution feature.
- **Admin account:** A dedicated admin account manages user creation and app settings. Regular users cannot create accounts
  or manage other users. The admin password is set via the `ADMIN_PASSWORD` environment variable on first run.
- **Session management:** JWT (JSON Web Tokens) for stateless session handling. Tokens are issued on login and stored
  client-side. This avoids server-side session state and works well with the SPA architecture.
- **External access:** The app is accessible from outside the home network. FastAPI serves TLS directly using a provided
  SSL certificate. TLS is optional at startup (can run plain HTTP during development) and enabled via configuration.

### Voice Input

- **Button-triggered listening:** The app uses the Web Speech API with a button click to start listening (not always-listening).
- **Supported commands:** add, remove, and check off items — with optional quantities and units.
  Default quantity is 1 when not specified.
- **TTS confirmation:** The app announces confirmation via the browser Speech Synthesis API after each
  voice command. TTS is only active during voice interaction, not for manual UI actions.

### Photos

- **Auto-resizing:** Photos are automatically resized to JPEG format with a maximum file size of 2 MB on upload.
- **Multiple photos per item:** Each item can have multiple photos (e.g., front and back of packaging), stored as a collection per item.

### Data Model

- **Three-table design:** The data is split across Products (catalog), Shopping List (active items), and
  History (event log). Products hold stable reference data (name, photos, stores, prices, category) and are
  reused across purchases. Shopping List entries reference a Product and hold only per-entry state (quantity,
  unit, added by/at). History records every action as an immutable event with full context (who, when, store,
  price, action type).
- **Single shared list:** The app uses one shopping list for the family rather than separate lists per store or purchase cadence.
- **Category suggestions:** Categories are suggested via web search (Google Custom Search API) based on item name, but users
  can override and define their own.

### Pricing

- **Optional price confirmation:** Prices are optionally confirmed when an item is checked off (during purchase).
  Users can see the actual price on the shelf and correct the suggested price if needed.
  Suggested prices come from Google Custom Search API results scraped via regex; falls back to manual entry.
- **Store selection at check-off:** Users can optionally select which store they are currently shopping at.
  The selection is cached per session to avoid repeated selection while shopping at the same store.

### Analytics

- **Built-in dashboard:** An analytical dashboard is included from the start to track spending patterns, contribution by
  family member, and purchase frequency.

### GPS / Proximity Alerts & Store Configuration

- **Deferred:** GPS-based proximity alerts and store location configuration are deferred for now.
  This feature can be added later once requirements and user experience are better defined.

### Data Archival

- **Manual removal:** Checked-off items are manually removed from history by users.
  Auto-archival is deferred for now; this feature may be revisited in the future with a longer retention period (e.g., 6 months).

### Home Assistant Integration

- **Deferred:** HASS webhook integration and entity state consumption are deferred for now.
  These can be added later if needed.

---

## Supported Stores (Initial Set)

- Stop & Shop
- Shop-Rite
- BJ's Wholesale Club
- Costco
- Whole Foods
- Trader Joe's

Additional stores can be added by any user in settings.

---

## Out of Scope (for now)

- Barcode scanning (possible future feature via browser camera API; could replace manual price confirmation at checkout)
- GPS-based proximity alerts and store geofencing
- Auto-archival of checked-off items (may revisit with ~6-month retention period)
- Home Assistant integration (webhook for adding items, entity state consumption)
- Automatic price lookup from store websites (web scraping, fragile)
- Recipe integration / meal planning
- Budget enforcement / spending limits
- Native iOS or Android apps

---

## Getting Started

### Build and Run with Docker

```bash
docker build -t shopping-list .
docker run -d \
  --name shopping-list \
  -p 8080:8080 \
  -v ~/shopping-list-data:/data \
  -e ADMIN_PASSWORD=your_secret_here \
  shopping-list
```

Open `http://localhost:8080` (or `http://<your-server-ip>:8080` from other devices on the network).

Log in with username **admin** and the password you set via `ADMIN_PASSWORD`. Create accounts for
family members from the admin user management page.

### Manage the Container

```bash
docker stop shopping-list     # stop
docker start shopping-list    # restart
docker logs shopping-list     # view logs
```

### Rebuild After Code Changes

```bash
docker stop shopping-list && docker rm shopping-list
docker build -t shopping-list .
docker run -d --name shopping-list -p 8080:8080 \
  -v ~/shopping-list-data:/data \
  -e ADMIN_PASSWORD=your_secret_here \
  shopping-list
```

The `-v ~/shopping-list-data:/data` volume mount persists the database and uploaded photos across
container rebuilds.

### Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ADMIN_PASSWORD` | Yes | `admin` | Password for the admin account (set on first run) |
| `PORT` | No | `8080` | HTTP port inside the container |
| `TLS_ENABLED` | No | `false` | Enable HTTPS |
| `TLS_CERT_FILE` | No | | Path to TLS certificate file (inside container) |
| `TLS_KEY_FILE` | No | | Path to TLS private key file (inside container) |
| `GOOGLE_CREDENTIALS_FILE` | No | | Path to JSON file with `api_key` and `search_engine_id` for Google Custom Search |
| `JWT_SECRET` | No | auto-generated | Secret key for signing JWT tokens |

