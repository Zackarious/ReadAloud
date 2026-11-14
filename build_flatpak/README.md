# Flathub Submission & Flatpak Packaging Guide

This directory contains the production-ready packaging files for publishing **ReadAloud** (`im.zackarious.ReadAloud`) to [Flathub](https://flathub.org).

---

## Files Included

1. **`im.zackarious.ReadAloud.yaml`**: The primary Flatpak manifest configured for Flathub. Fetches upstream source from GitHub at tag `v1.8.19` (`97cc299cff4c35f225005d049784f8ad200acbb4`).
2. **`pip-dependencies.json`**: Pinned, offline Python wheel dependencies with SHA-256 integrity verification for both `x86_64` and `aarch64`.
3. **`flathub.json`**: Specifies architecture build targets (`x86_64` and `aarch64`).
4. **`build_flatpak.sh`**: Helper script to test-build and install the Flatpak locally.

---

## Step-by-Step Submission Process to Flathub

Flathub requires all new applications to be submitted via a Pull Request to [flathub/flathub](https://github.com/flathub/flathub).

> **Note on Flathub Generative AI Policy**: Flathub strictly requires that the PR submission and review interaction on GitHub is performed directly by the human developer.

### Step 1: Fork and Clone `flathub/flathub`

```bash
# 1. Fork flathub/flathub on GitHub via the web UI or gh CLI:
gh repo fork flathub/flathub --clone=true

# 2. Navigate to your local clone of the fork:
cd flathub

# 3. Create a new branch named after the application ID:
git checkout -b im.zackarious.ReadAloud
```

### Step 2: Copy the Package Files into the Root of the Fork

Copy the 3 manifest files directly to the root of your `flathub` repository branch:

```bash
cp /path/to/ReadAloud/build_flatpak/im.zackarious.ReadAloud.yaml .
cp /path/to/ReadAloud/build_flatpak/pip-dependencies.json .
cp /path/to/ReadAloud/build_flatpak/flathub.json .
```

### Step 3: Commit and Push

```bash
git add im.zackarious.ReadAloud.yaml pip-dependencies.json flathub.json
git commit -m "Add im.zackarious.ReadAloud"
git push -u origin im.zackarious.ReadAloud
```

### Step 4: Open Pull Request on Flathub

```bash
gh pr create --repo flathub/flathub \
  --base master \
  --head Zackarious:im.zackarious.ReadAloud \
  --title "Add im.zackarious.ReadAloud" \
  --body "Add ReadAloud: An offline, private text-to-speech reader for Linux crafted with GTK4 and Libadwaita."
```
*(Or open the PR directly through the GitHub web UI).*

---

## What Happens Next

1. **Automated CI**: Flathub's buildbot will automatically trigger test builds for both `x86_64` and `aarch64` architectures.
2. **Maintainer Review**: A Flathub reviewer will review the permissions, sandbox args, and metadata.
3. **Repository Creation**: Upon merge, Flathub will automatically create `https://github.com/flathub/im.zackarious.ReadAloud` and invite your GitHub account (`Zackarious`) as maintainer.
4. **Publication**: The app will automatically build and publish to `https://flathub.org/apps/im.zackarious.ReadAloud`.

---

## Post-Publication: Developer Verification

To obtain the verified checkmark on Flathub:
1. Log in to [Flathub Developer Portal](https://flathub.org/) using your GitHub account.
2. Under your app dashboard, go to **Verification**.
3. Follow the verification prompt (DNS TXT record `_flathub.zackarious.im` or website file `/.well-known/org.flathub.VerifiedApps.txt`).
