# Home Assistant Integration

## Setup
- HA installation: **HA Container** (plain Docker, no Supervisor/add-ons/Ingress)
- Both HA and shopping-list containers are behind **Traefik**
- Shopping list embedded in HA via **Webpage card** (type: `iframe`) on Lovelace dashboards
- Also available as **Webpage Dashboard** in the HA sidebar (Settings → Dashboards → Add → Webpage)
- Auth: users log into shopping list separately (30-day JWT), no SSO

## Webpage Card Config (with microphone support)
```yaml
type: iframe
url: "https://shopping.yourdomain.com"
aspect_ratio: "200%"
allow: "fullscreen; microphone"
disable_sandbox: true
```
- `allow: "fullscreen; microphone"` — sets iframe Permissions Policy for Web Speech API
- `disable_sandbox: true` — removes sandbox restrictions that block microphone even with `allow`
- Both are required for voice commands to work

## Key Findings
- `panel_iframe` was **removed** from HA — replaced by Webpage Dashboard and Webpage card
- HA Container does NOT support add-ons or Ingress (only HA OS / HA Supervised do)
- HA Ingress (for add-ons) forwards user identity via trusted headers:
  - `X-Remote-User-Id`, `X-Remote-User-Name`, `X-Remote-User-Display-Name`
  - Set server-side from session data, spoofing prevented by stripping incoming values
  - Not available in HA Container mode
- HA iframe card source: `allow` config maps to iframe `allow` attribute (default: `"fullscreen"`)
