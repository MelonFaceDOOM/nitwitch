# Nitwitch

Django site for writing, pics, and movienights, laid out on a fixed grid-paper theme.

## Running locally

```powershell
python manage.py runserver
```

Set `DJANGO_DEVELOPMENT=1` (in `.env` or the environment) to run in dev mode.
See `.env.example` for all settings, including the SSH tunnel used to reach the
server's Postgres from another machine.

## Movienights database

The **movienights** section uses the Discord movie-night bot database. It uses
the same host/port as Nitwitch (including the SSH tunnel when enabled), but a
**different database name/user/password**:

```
MOVIENIGHT_DB_NAME=...
MOVIENIGHT_DB_USER=...
MOVIENIGHT_DB_PASSWORD=...
```

Models are **unmanaged** (`managed = False`). Do **not** run
`python manage.py migrate` expecting it to create or alter that schema — Django
is blocked from migrating the `movienight` database alias. Browse at
`/movienights/`.

Write actions (suggest, remove, endorse, rate, review, transfer, …) live in
`movienights/actions.py` and mirror melonbot Core rules. The DB role therefore
needs **SELECT** plus **INSERT/UPDATE/DELETE** on `movies`, `ratings`,
`endorsements`, and `reviews`, and **INSERT/UPDATE** on `users` / `guilds` for
OAuth display-name upserts. Read helpers for browse/stats live in
`movienights/queries.py`; temporary JSON verify routes are under
`/movienights/<guild_id>/api/<kind>/`.

### Display names (bot-owned cache)

Snowflake ids alone are hard to read. The site expects optional cache columns
that the **Discord bot** maintains (Nitwitch only reads them):

```sql
ALTER TABLE guilds
  ADD COLUMN IF NOT EXISTS name VARCHAR(128),
  ADD COLUMN IF NOT EXISTS icon_url TEXT,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS username VARCHAR(64),
  ADD COLUMN IF NOT EXISTS global_name VARCHAR(64),
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;
```

Run these on the movienight database (bot owns the schema). Prefer the
melonbot migration script (idempotent):

```text
# from the melonbot repo, with PSQL_CREDENTIALS pointed at the target DB
python migrations/migration_2026_07_18_display_names.py
```

See melonbot `migrations/README.md` for the full sync hooks and the
dev → test → prod runbook.

**How names get populated (bot):**

- Automatically on movie commands via `get_user_id` / `get_guild_id` upserts.
- Automatically on guild join/update and user/member rename events.
- One-shot backfill: bot owner runs `!sync_names` after migrate (no nightly job).

Display rule on the site: `global_name` → `username` → truncated id.

### Viewer context (Discord OAuth, not site login)

The Movienights landing page shows only title/description and **Verify with
Discord** until OAuth succeeds. After verify, it lists **your** Discord servers
that already exist in the melonbot DB (OAuth `identify guilds`, intersected with
`guilds` rows). Deep links to a guild hub/movies require that membership.

That is not Nitwitch email/password login. Rating, reviewing, endorsing, and
other movie actions are available on the site once verified (same rules as
melonbot).

Register a Discord Application → OAuth2 and set:

```
DISCORD_CLIENT_ID=...
DISCORD_CLIENT_SECRET=...
```

Register **both** redirect URIs on the same Discord app:

- `http://127.0.0.1:8000/movienights/oauth/discord/callback/` (dev)
- `https://nitwitch.com/movienights/oauth/discord/callback/` (prod)

`DISCORD_OAUTH_REDIRECT_URI` defaults from `DJANGO_DEVELOPMENT` (local vs
nitwitch.com). Override in `.env` only if you need a non-default host. Scopes:
`identify guilds`. Users who verified with `identify` only should Clear and
verify again so Discord prompts for the guilds permission.

On success Nitwitch upserts `users.username` / `global_name` (and refreshes
guild names when possible) if the movienight DB role allows writes. If the role
is read-only, the viewer still works when that Discord id already exists (e.g.
after melonbot use); guild membership still comes from the OAuth guild list.

## Users and admin

### The model

- The user model is `accounts.CustomUser` (extends Django's `AbstractUser`).
- Login is by **email** (via django-allauth); usernames aren't used to log in.
- There is exactly **one role bit: `is_staff`**, which the whole site treats as
  "admin". Superusers are implicitly staff, so they count as admins too. The gate
  lives in [`accounts/permissions.py`](accounts/permissions.py) (`is_admin` /
  `admin_required`) and is used both in views and, as `user.is_staff`, in templates.
- **Non-admins can't do anything** beyond browsing and IP-based commenting/voting.
  Creating, editing, and deleting articles/photo albums/adventures all require admin.

### Signup behavior

- **Dev** (`DJANGO_DEVELOPMENT=1`): signup creates an account with **no email
  confirmation**, and it's **automatically made admin** (see
  [`accounts/signals.py`](accounts/signals.py)). Frictionless local testing.
- **Prod**: signup sends a **confirmation email**. The user clicks the link to
  activate a **non-admin** account. They can't do anything until an admin
  promotes them.

### Creating the first admin

New prod signups are non-admin, so bootstrap the first admin from the shell:

```powershell
python manage.py createsuperuser
```

Enter an email and password. A superuser is also staff, so this account is an
admin and can log in and promote others.

### Promoting / demoting admins

Log in as an admin and go to **`/admin-controls/manage/`**. The Users table has
**Promote** / **Demote** buttons that flip `is_staff`. Guardrails:

- Superusers can't be demoted here (use `/admin/` if you really must).
- You can't demote yourself.

Django's built-in admin at `/admin/` also works for a superuser who prefers it.

## Email (prod)

In dev, email is printed to the console. In prod the site sends real mail over
SMTP via **Amazon SES**.

### Amazon SES setup

1. In the [AWS Console](https://console.aws.amazon.com/), open **Amazon SES**
   and pick a region (e.g. **US East (N. Virginia) / us-east-1**). Remember it —
   the SMTP hostname depends on it.
2. **Verify your domain** (recommended): SES → **Identities** → **Create
   identity** → Domain → `nitwitch.com`. Add the DNS records SES shows (DKIM
   CNAMEs; optionally DMARC/SPF) in Cloudflare, same idea as any provider.
   Wait until the identity status is **Verified**.
3. **Create SMTP credentials**: SES → **SMTP settings** → **Create SMTP
   credentials**. This creates an IAM user and shows an SMTP username +
   password once — save them. These are **not** your AWS root/access keys.
4. Put the following in `.env` **on the server** (prod):

   ```
   EMAIL_HOST=email-smtp.us-east-1.amazonaws.com
   EMAIL_PORT=587
   EMAIL_HOST_USER=<SES SMTP username>
   EMAIL_HOST_PASSWORD=<SES SMTP password>
   DEFAULT_FROM_EMAIL=no-reply@nitwitch.com
   ```

   If you used another region, change the host (examples:
   `email-smtp.us-west-2.amazonaws.com`, `email-smtp.eu-west-1.amazonaws.com`).
   `DEFAULT_FROM_EMAIL` must be on your verified domain.
5. **Sandbox vs production:** New SES accounts start in the **sandbox** — you
   can only send to addresses you have also verified. For real signups, request
   **production access** (SES → Account dashboard → Request production access).
   Approval is usually quick for a transactional signup site; say you only send
   account confirmation email, no marketing blasts.

Pricing is usage-based (pennies per thousand). No monthly minimum for SMTP at
typical hobby volume.

## Dependencies

Install extras used by the tunnel and env loading:

```powershell
pip install sshtunnel python-dotenv
```
