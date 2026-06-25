# Messenger Auto‑Reply — Meta Configuration Guide

Flowtina replies to Facebook **Page** direct messages automatically: Meta delivers
each DM to our webhook, the message is queued, and a background poller sends a
memory‑aware AI reply (debounced and de‑duplicated). The application code is ready;
this guide covers the **Meta‑side configuration** required to make it work with
real fans.

> TL;DR — to reply to **real fans** (not just app admins/testers) you must:
> 1. Add **Messenger** + **Webhooks** products to the app.
> 2. Request and pass **App Review** for `pages_messaging`, then set the app **Live**.
> 3. **Subscribe** the webhook to the `messages` field and **subscribe the Page** to the app.
> 4. Use a Page token that carries `pages_messaging`.

---

## 1. Prerequisites

| Item | Value |
| --- | --- |
| Public webhook URL | `https://flowtina.fechtin.com/api/v1/messenger/webhook` |
| Verify token (`hub.verify_token`) | must equal env `MESSENGER_VERIFY_TOKEN` |
| Signature secret | env `FACEBOOK_APP_SECRET` (validates `X‑Hub‑Signature‑256`) |
| Page token scope | `pages_messaging` (plus existing `pages_read_engagement`, `pages_manage_engagement` for comments) |

Set the env vars on the server before configuring Meta:

```bash
# backend/.env
MESSENGER_VERIFY_TOKEN=<a-long-random-string-you-choose>
FACEBOOK_APP_SECRET=<from App Dashboard → Settings → Basic → App Secret>
```

Restart the backend so the webhook verifies with the new token.

---

## 2. Add products to the Meta app

In **developers.facebook.com → My Apps → <your app> → Add Product**:

- **Messenger**
- **Webhooks**

(Business type app recommended; a personal app cannot pass review for `pages_messaging`.)

---

## 3. Configure the Webhook (callback URL + verification)

**Messenger → Settings → Webhooks → Add Callback URL** (or **Webhooks** product → Page):

1. **Callback URL:** `https://flowtina.fechtin.com/api/v1/messenger/webhook`
2. **Verify Token:** the exact value of `MESSENGER_VERIFY_TOKEN`.
3. Click **Verify and Save**. Meta sends `GET …?hub.mode=subscribe&hub.verify_token=…&hub.challenge=…`;
   our endpoint echoes the challenge when the token matches. A green check = success.
4. Under **Webhook Fields**, subscribe to:
   - **`messages`** (required — inbound DMs)
   - `messaging_postbacks` (optional — button taps)

> If verification fails: confirm the URL is public over HTTPS, the token matches
> exactly, and the backend is running.

---

## 4. Subscribe the Page to the app (easy to miss!)

A verified webhook is **not enough** — each Page must be subscribed to the app or no
events are delivered.

- **Messenger → Settings → "Add or remove Pages"** → connect the Page, **or**
- API call with a Page token that has `pages_messaging`:

```bash
curl -X POST "https://graph.facebook.com/v21.0/<PAGE_ID>/subscribed_apps" \
  -d "subscribed_fields=messages,messaging_postbacks" \
  -d "access_token=<PAGE_ACCESS_TOKEN>"
# -> {"success": true}
```

Verify it stuck:

```bash
curl "https://graph.facebook.com/v21.0/<PAGE_ID>/subscribed_apps?access_token=<PAGE_ACCESS_TOKEN>"
```

---

## 5. Page token with `pages_messaging`

In Flowtina, import the Page with a token that includes `pages_messaging`:

- **Graph API Explorer** or a **System User** token (recommended for long‑lived,
  non‑expiring tokens) with permissions:
  `pages_messaging`, `pages_read_engagement`, `pages_manage_engagement`,
  `pages_manage_metadata`, `pages_show_list`.
- Paste the token into Flowtina's Facebook page import; the app exchanges it for
  per‑Page tokens and stores them encrypted.
- In the page's engagement settings, enable **Auto‑reply to messages**.

---

## 6. App Review — required for real fans

While the app is in **Development mode**, the webhook only fires for people with a
**role on the app** (admins, developers, testers). To message the **general public**
you must:

1. **Messenger → App Review → Permissions and Features** → request **`pages_messaging`**
   (Advanced Access).
2. Provide the required materials:
   - Screencast showing the message → auto‑reply flow.
   - A clear description of the use case.
   - Valid **Privacy Policy URL** and app icon.
3. Complete **Business Verification** (Meta Business Suite).
4. Once approved, **toggle the app to Live** (top bar).

Until then, you can fully test by messaging the Page from an **admin/tester** account.

---

## 7. The 24‑hour messaging window

Meta only allows free‑form messages within **24 hours** of the user's last message.
Auto‑reply via webhook always responds to a fresh inbound message, so it stays inside
this window — no message tags or one‑time notification tokens are needed. Do **not**
attempt to send proactive messages outside 24h; they will be rejected unless sent
under an approved message tag.

---

## 8. How Flowtina processes messages (for operators)

- The webhook **only queues** messages (`messenger_events` table) and returns `200`
  immediately, so Meta never times out or retries.
- A scheduler job (`process_messenger_inbox`, every `MESSENGER_INBOX_TICK_SECONDS`,
  default 5s) sends the replies out of band:
  - **Debounce / coalesce** — a follower's rapid‑fire lines are merged into **one**
    reply once they pause for `MESSENGER_DEBOUNCE_SECONDS` (default 6s).
  - **Dedupe** — duplicate webhook deliveries are ignored by Meta message id (`mid`).
  - **Retry** — failed sends retry up to `MESSENGER_MAX_ATTEMPTS` (default 3), then
    the message is marked `failed` so it stops blocking the queue.
  - **UX** — the follower sees **Seen** + a typing indicator while the reply is
    generated.

### Tunable settings (env / `backend/app/core/config.py`)

| Setting | Default | Meaning |
| --- | --- | --- |
| `MESSENGER_INBOX_TICK_SECONDS` | `5` | How often the reply poller runs |
| `MESSENGER_DEBOUNCE_SECONDS` | `6` | Pause before a burst is answered as one reply |
| `MESSENGER_COALESCE_MAX` | `10` | Max queued messages merged into one reply turn |
| `MESSENGER_MAX_ATTEMPTS` | `3` | Send retries before giving up on a message |

---

## 9. Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| Webhook won't verify | Token mismatch, URL not public/HTTPS, backend down |
| Verified but no replies to fans | App still in Development, or `pages_messaging` not approved |
| No events at all | Page not subscribed to the app (Section 4) |
| `(#10) … pages_messaging` error in logs | Page token missing `pages_messaging` scope — re‑import token |
| Replies duplicated | (Handled) dedupe by `mid` + single‑instance poller |
| Reply is slow | Increase poller cadence (`MESSENGER_INBOX_TICK_SECONDS`) or lower debounce |
