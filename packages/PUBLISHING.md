# Publishing checklist

**Status (updated 2026-10-25 ~04:40 KST from the npm registry, PyPI and the repo's Actions runs, read-only):** npm `@webextract/sdk`, `@webextract/ai-sdk`, `@webextract/langchain` are published at **0.1.0** (2026-10-21, 20:38 / 20:39 / 20:47 KST, by hand) and **0.1.1** (2026-10-25, 04:31–04:32 KST, by `publish-npm.yml` through npm Trusted Publisher with provenance; `latest` = 0.1.1; each package also has the `0.0.0-stage` placeholder that staged publishing creates). PyPI `webextract-sdk` and `langchain-webextract` are published at **0.1.0** (2026-10-21, 21:04 / 21:05 KST, by `publish-pypi.yml` on tag `py-v0.1.0`) and **0.1.1** (2026-10-25, 04:03 KST, by `publish-pypi.yml` on tag `py-v0.1.1`). npm Trusted Publisher (§2) is set up, and the workflows (§0) are in the repo's `.github/workflows/`. The checklist items below are the original first-publish plan and have not been re-ticked.

Decided by 来禄: accounts registered with the company email, and **the boss does the first publish**.

**npm names are scoped (changed 2026-10-21 20:33 KST):** npm rejected the unscoped `webextract` with 403 "Package name too similar to existing package web-extract". The npm user account `webextract` owns the `@webextract` scope, so the JS packages are `@webextract/sdk`, `@webextract/ai-sdk` and `@webextract/langchain`. Directory names under `js/` are unchanged (`js/webextract`, `js/webextract-ai-sdk`, `js/langchain-webextract`). PyPI names: **`webextract-sdk`** (changed 2026-10-21 20:53 KST, because PyPI does not allow `webextract`; the import name stays `webextract`) and `langchain-webextract` (depends on `webextract-sdk>=0.1.0,<0.2`).
🔐 = a human must sign in, pass 2FA or approve. An agent cannot do these.

## 0. Before any publish (repo maintainer)
1. [ ] Copy `packages/` into the repo `nyx464664816-stack/webextract` at `packages/` (keep `js/`, `python/`). Leave out `dist-local/`, `node_modules/` and `.venv/` (see `.gitignore`).
2. [ ] Make sure `publish-npm.yml` and `publish-pypi.yml` are in the repo's `.github/workflows/` (they are there now; the old `ci/` staging folder no longer exists).
3. [ ] The repo must be **public**, otherwise npm won't generate provenance. Every package.json has `repository.url = git+https://github.com/nyx464664816-stack/webextract.git`, and npm requires an exact match.
4. [ ] 🔐 GitHub → Settings → Environments: create `npm`, `pypi-sdk` and `pypi`. Optionally add required reviewers (the boss) as a manual gate.
5. [ ] npm names: done (published 0.1.0). PyPI: check again that https://pypi.org/project/webextract-sdk/ and https://pypi.org/project/langchain-webextract/ still return 404. A PyPI pending publisher does **not** reserve a name.
6. [ ] Run locally: `cd packages/js && npm ci && npm test`, `cd packages/python && pytest`, then `./check-artifacts.sh` → must print `CLEAN`.

## 1. npm: first publish by hand (boss) 🔐 — done for 0.1.0 (all three, 2026-10-21)
Trusted publishing can only be configured on a package that already exists, so version 0.1.0 goes up by hand.
1. [ ] 🔐 Create an npmjs.com account with the company email. Turn on 2FA (security key or TOTP). The boss holds the 2FA.
2. [ ] 🔐 On the boss's machine (not this box): `npm login` (browser + 2FA).
3. [ ] Order matters, because the tool packages depend on `@webextract/sdk@^0.1.0`. Scoped packages are private by default, so `--access public` (also set in each `publishConfig`) is required:
   ```bash
   cd packages/js && npm ci && npm run build && npm test
   (cd webextract && npm publish --access public)            # @webextract/sdk        🔐 2FA prompt
   (cd webextract-ai-sdk && npm publish --access public)     # @webextract/ai-sdk     🔐
   (cd langchain-webextract && npm publish --access public)  # @webextract/langchain  🔐
   ```
   Don't pass `--provenance` locally. It only works in CI.
4. [ ] `npm logout` on that machine.

## 2. npm: Trusted Publisher (web form, per package) 🔐
npmjs.com → Packages → *package* → Settings → Trusted publishing → GitHub Actions. Do this for **each** of `@webextract/sdk`, `@webextract/ai-sdk`, `@webextract/langchain`:

| Field | Value |
|---|---|
| Organization or user | `nyx464664816-stack` |
| Repository | `webextract` |
| Workflow filename | `publish-npm.yml` (file name only) |
| Environment name | `npm` |
| Allowed actions | tick **npm publish**. Configs created after 2026-09-03 default to `npm stage publish` only. If you keep stage-only, change the workflow to `npm stage publish` and approve each release with 2FA |

- [ ] ⚠️ A new config **expires if it doesn't publish successfully within 2 days**. Only create it when you are ready to push a `js-v0.1.1` tag (bump all three versions first).
- [ ] After the first OIDC publish succeeds, go to Settings → Publishing access → "Require two-factor authentication and disallow tokens" 🔐.
- CI needs npm ≥ 11.5.1 and Node ≥ 22.14. The workflow uses Node 24 and upgrades npm.

## 3. PyPI 🔐
Option A (recommended): no token ever exists.
1. [ ] 🔐 Create a pypi.org account with the company email, with 2FA (required by PyPI).
2. [ ] 🔐 Account → Publishing → "Add a new pending publisher" (GitHub). Do it twice, once per project:

| Field | `webextract-sdk` | `langchain-webextract` |
|---|---|---|
| PyPI Project Name | `webextract-sdk` | `langchain-webextract` |
| Owner | `nyx464664816-stack` | `nyx464664816-stack` |
| Repository name | `webextract` | `webextract` |
| Workflow name | `publish-pypi.yml` | `publish-pypi.yml` |
| Environment name | `pypi-sdk` | `pypi` |

PyPI refuses two pending publishers with identical settings, so `webextract-sdk` uses the GitHub environment `pypi-sdk` and `langchain-webextract` uses `pypi`. In `publish-pypi.yml` the job `publish-webextract-sdk` runs in `pypi-sdk`; `publish-langchain-webextract` runs in `pypi` and `needs` the sdk job (changed 2026-10-21 KST).

3. [ ] 🔐 The boss pushes tag `py-v0.1.0`, or runs the workflow by hand and approves the `pypi-sdk` and `pypi` environments. The workflow publishes `webextract-sdk` first, then `langchain-webextract`.

Option B (only if a manual first upload is required): the boss creates a project-scoped API token and runs `python -m build` + `twine upload` on their own machine 🔐. Afterwards, add the normal trusted publisher with the same fields and delete the token.

## 4. After publishing
- [ ] Install-test from the registries: `npm i @webextract/ai-sdk ai zod` and `pip install webextract-sdk langchain-webextract`, then run `js/smoke/smoke-free.mjs` / `python/smoke/smoke_free.py`.
- [x] `langchain-tests` standard tests (ToolsUnitTests + ToolsIntegrationTests) are wired into `langchain-webextract` (Python, PyPI): see STANDARD-TESTS.md.
