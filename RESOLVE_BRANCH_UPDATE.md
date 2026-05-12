# Unable to update branch? (Fix guide)

Use this when GitHub says it cannot update your PR branch.

## Fastest fix (GitHub UI)

1. Open the PR → **Resolve conflicts**.
2. For conflicts between old AI code and new RSS code, choose:
   - **Accept current change** for:
     - `update_news.py`
     - `requirements.txt`
     - `README.md`
     - `index.html` (if present)
     - `.github/workflows/update_news.yml` (if present)
   - **Accept both changes** for `data.json`, then regenerate it.
3. Remove all conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`) if any remain.
4. Click **Mark as resolved** for each file.
5. Commit merge.

Then regenerate snapshot data locally (or in Codespaces):

```bash
python update_news.py
git add data.json
git commit -m "Regenerate data.json after conflict resolution"
git push
```

## Reliable fix (local terminal)

```bash
# from your PR branch
git fetch origin
git merge origin/main

# keep RSS/no-AI versions for core files
git checkout --ours update_news.py requirements.txt README.md index.html .github/workflows/update_news.yml

# keep both for data.json, then regenerate
# (if data.json conflicted)
python update_news.py

git add update_news.py requirements.txt README.md index.html .github/workflows/update_news.yml data.json
git commit -m "Resolve merge conflicts keeping RSS pipeline"
git push
```

## If GitHub still says “can’t update branch”

- Ensure the branch is not protected.
- Ensure you have write permission to the fork/repo.
- If the PR branch is stale, run:

```bash
git fetch origin
git rebase origin/main
git push --force-with-lease
```

Use `--force-with-lease` (not `--force`) to avoid overwriting others’ work.
