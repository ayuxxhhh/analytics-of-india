
# analytics-of-india
# Analytics of India

A static news website that auto-publishes:
- Top **20 India headlines**
- Top **10 global headlines**
- Manually written in-house reports

No AI generation is required.

## What changed

- `update_news.py` now fetches RSS headlines directly (no Gemini/OpenAI).
- The site renders separate India and Global sections.
- GitHub Actions updates `data.json` every 24 hours.

## Local run

```bash
pip install -r requirements.txt
python update_news.py
```

## Automation schedule

Workflow: `.github/workflows/update_news.yml`

- Runs daily at `00:00 UTC` (once every 24 hours).
- Also supports manual trigger via **workflow_dispatch**.

## Step-by-step: Free journalist backend (recommended path)

You asked for a backend that journalists can log into and publish from the site itself.
This is the easiest free stack:

### Stack
1. **Supabase** (free tier)
   - Auth (email/password login)
   - Postgres DB for articles/reports
   - Row Level Security for role-based posting
2. **Vercel** (free tier)
   - Hosts frontend + serverless API routes
3. **GitHub Actions**
   - Keep current RSS pull automation if you want static snapshots too

### Step 1: Create Supabase project
- Create project at supabase.com.
- Create tables:
  - `profiles(id uuid PK references auth.users, role text)`
  - `articles(id uuid PK, title text, body text, category text, region text, source_link text, created_at timestamptz default now(), author_id uuid)`
- Enable RLS on both tables.

### Step 2: Add role-based policies
- Allow read for all published articles.
- Allow insert/update only if:
  - user is authenticated
  - `profiles.role IN ('journalist', 'editor', 'admin')`

### Step 3: Add login page on website
- Add `/login` page with Supabase auth.
- Add `/dashboard` page with create/edit article form.
- Restrict dashboard to logged-in users.

### Step 4: Share access with journalists
- Create accounts from Supabase dashboard or invite by email.
- Set role in `profiles` table.
- Send them login URL + password reset flow.

### Step 5: Publish workflow
- Journalist submits article in dashboard.
- Article appears instantly from DB (dynamic mode), or
- Nightly GitHub Action exports DB content into `data.json` (hybrid static mode).

### Step 6: Secure and moderate
- Add editor approval flag (`status: draft/review/published`).
- Only published articles appear publicly.
- Add audit columns (`updated_at`, `approved_by`).

If you want, next PR can implement **Step 1–3** directly in this repo.


## If your PR shows merge conflicts (exact fix)

If conflicts are in `README.md`, `requirements.txt`, and `update_news.py` exactly like your screenshot,
use this resolution strategy:

1. **Keep current change** for all three files (the RSS/no-AI version).
2. Remove all conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`).
3. Verify final files are:
   - `requirements.txt` contains only `requests`
   - `update_news.py` contains RSS fetch logic (`INDIA_TOP_STORIES_RSS` and `GLOBAL_TOP_STORIES_RSS`) and no `google-genai`/`openai` imports
4. Run:
   ```bash
   python -m py_compile update_news.py
   python update_news.py
   ```
5. Commit conflict resolution and push.

### CLI one-liner approach

```bash
git checkout --ours README.md requirements.txt update_news.py
git add README.md requirements.txt update_news.py
git commit -m "Resolve merge conflicts keeping RSS pipeline"
git push
```

After push, GitHub PR should become mergeable.


### Conflict decision matrix (quick answer)

If conflicts are from the old AI branch vs the new RSS branch, use:

- `update_news.py` → **Accept current change**
- `requirements.txt` → **Accept current change**
- `README.md` → **Accept current change**
- `index.html` (if it conflicts) → **Accept current change**
- `.github/workflows/update_news.yml` (if it conflicts) → **Accept current change**
- `data.json` (if it conflicts) → **Accept both changes**, then run `python update_news.py` and commit the regenerated file

Reason: we want to keep the RSS/no-AI architecture and only refresh generated news snapshot afterwards.


For a dedicated troubleshooting walkthrough, see `RESOLVE_BRANCH_UPDATE.md`.
