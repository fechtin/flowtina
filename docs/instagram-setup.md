# Instagram Cross‑Posting — Meta Configuration Guide

Flowtina can publish a single post to **both** a Facebook Page and its linked
**Instagram** account at once. Instagram uses the same Meta Graph API as Facebook:
an Instagram **Business/Creator** account is linked to a Facebook Page and shares
that Page's access token. The application code is ready; this guide covers the
**Meta‑side configuration** required to publish to a real Instagram account.

> TL;DR — to publish to Instagram you must:
> 1. Have an Instagram **Business or Creator** account, **linked to a Facebook Page**.
> 2. Use a Page token that carries `instagram_basic` + `instagram_content_publish`
>    (plus `pages_show_list`, `pages_read_engagement`).
> 3. Request and pass **App Review** for those Instagram scopes, then set the app **Live**.
> 4. Make sure every post has an **image** and a **publicly reachable image URL**
>    (set `PUBLIC_BASE_URL` so locally uploaded images are fetchable by Meta).

---

## 1. How it works in Flowtina

- A connected **Page** stores its linked Instagram account (`instagram_user_id`,
  `instagram_username`), discovered automatically on import/connect.
- The **Facebook** page (Pages → a Page → *Publishing platforms*) shows two toggles:
  **Publish to Facebook** and **Publish to Instagram**. Instagram turns on
  automatically when an IG account is detected.
- On publish, the post fans out to every enabled platform. Each platform gets its
  own history row; a retry skips a platform that already succeeded (no duplicates).
- Instagram publishing is a **two‑step** Graph flow: create a media container
  (`POST /{ig-user-id}/media` with `image_url` + `caption`) then publish it
  (`POST /{ig-user-id}/media_publish`).

---

## 2. Prerequisites

| Item | Value |
| --- | --- |
| Instagram account type | **Business** or **Creator** (not personal) |
| Linked Facebook Page | the IG account must be linked to the Page in its settings |
| Page token scopes | `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement` |
| Public image URL | every IG post needs an image reachable by Meta's servers |
| `PUBLIC_BASE_URL` | env on the server, used to expose locally uploaded images |

```bash
# backend/.env
PUBLIC_BASE_URL=https://flowtina.fechtin.com
```

Posts that carry a public `image_url` work without `PUBLIC_BASE_URL`; locally
uploaded images are served (unauthenticated, by UUID) at
`/<PUBLIC_BASE_URL>/api/v1/public/posts/{post_id}/image` for the brief window
between upload and publish, and removed once publishing succeeds.

---

## 3. Link Instagram to the Facebook Page

In **Facebook → the Page → Settings → Linked accounts → Instagram** (or in the
Meta Business Suite), connect the Instagram **Business/Creator** account to the
Page. One Page links at most one Instagram account.

To convert a personal account: **Instagram app → Settings → Account type and
tools → Switch to professional account → Business/Creator**.

---

## 4. Add products & scopes to the Meta app

In **developers.facebook.com → My Apps → <your app>**:

- Add the **Instagram Graph API** product (and **Facebook Login** / **Webhooks**
  if not already present).
- The token you use to import the Page must be granted, in addition to the
  existing Page scopes:
  - **`instagram_basic`** — read the linked IG account id/username.
  - **`instagram_content_publish`** — create and publish IG media.

Generate/refresh the token (Graph API Explorer or a System User token), then
**re‑import the Page** in Flowtina (Pages → *Import pages*) so the new token and
the discovered Instagram account are stored.

(Business‑type app recommended; a personal app cannot pass review for the
Instagram publishing scopes.)

---

## 5. App Review & Live mode

Like Messenger, publishing to **real** Instagram accounts requires **App Review**:

1. Submit `instagram_basic` and `instagram_content_publish` for review with a
   screencast showing the connect → publish flow.
2. Once approved, set the app to **Live**.

Before approval, publishing only works for users with a **role on the app**
(admins/developers/testers) and their own linked IG accounts — enough to test
end‑to‑end.

---

## 6. Image & content requirements

Instagram is stricter than Facebook feed posts:

- **An image is mandatory** — Instagram has no text‑only post. A post with no
  image fails the Instagram leg (Facebook still succeeds if enabled).
- The image must be a **public JPEG/PNG URL** reachable by Meta (no binary upload,
  unlike Facebook `/photos`).
- Caption ≤ **2,200 characters**, ≤ **30 hashtags** (Flowtina reuses the post's
  body + hashtags as the caption).
- Aspect ratio must be within Instagram's allowed range (roughly 4:5 to 1.91:1).

---

## 7. Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| Toggle "Publish to Instagram" is disabled | No IG account linked to the Page, or the token lacked `instagram_basic` on import. Link the IG account, refresh the token, re‑import. |
| `Instagram needs a public image URL…` | The post has only a locally uploaded image and `PUBLIC_BASE_URL` is empty, or it has no image at all. Set `PUBLIC_BASE_URL` or attach a public `image_url`. |
| `Instagram posts require an image` | The post is text‑only. Add an image. |
| `(#10) Application does not have permission` | Token missing `instagram_content_publish`, or app not in Live mode for non‑role users. |
| Facebook publishes but Instagram fails | Expected partial success: the post is marked published, the failure is recorded per‑platform, and a retry re‑attempts only Instagram. |

---

## 8. Comment & DM auto-reply (optional)

Beyond publishing, Flowtina can auto-reply to Instagram **comments** and **direct
messages**, mirroring the Facebook comment engagement and Messenger DM features.
Enable them per page under **Pages → a Page → Engagement** (the Instagram toggles
appear once an IG account is linked).

| Feature | How it runs | Extra scope | App Review |
| --- | --- | --- | --- |
| Comment auto-reply | Polls the IG account's recent media and replies to new comments (`POST /{ig-comment-id}/replies`). No webhook needed. | `instagram_manage_comments` | Required for public use |
| DM auto-reply | Webhook-driven: Meta delivers Instagram messages to the same callback as Messenger; replies go out via `POST /{ig-user-id}/messages`. | `instagram_manage_messages` | Required for public use |

Instagram does not expose a comment "like" via the API, so only auto-reply is
available for IG (no auto-like).

### Webhook for Instagram DMs

DMs (not comments) need the Instagram webhook configured in the Meta App:

1. **Products → Webhooks → Instagram** (or **Messenger → Instagram settings**).
2. **Callback URL:** `https://flowtina.fechtin.com/api/v1/messenger/webhook`
   (the same endpoint as Messenger — it routes `object == "instagram"` events).
3. **Verify Token:** the value of `MESSENGER_VERIFY_TOKEN`.
4. Subscribe to the **`messages`** field and connect the Instagram account.

The webhook handler ignores comment webhooks; comment auto-reply uses polling, so
you do **not** need to subscribe to the `comments` field for it to work.

---

## 9. Quick checklist

- [ ] Instagram account is **Business/Creator** and **linked to the Page**.
- [ ] Token has `instagram_basic` + `instagram_content_publish`; Page re‑imported.
- [ ] App Review passed for those scopes; app is **Live** (for real accounts).
- [ ] `PUBLIC_BASE_URL` set (for locally uploaded images).
- [ ] Posts include an image within Instagram's size/ratio limits.
- [ ] "Publish to Instagram" toggle is on for the Page.
</content>
