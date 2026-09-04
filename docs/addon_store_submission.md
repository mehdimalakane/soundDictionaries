# NVDA Add-on Store Submission & Future Updates Guide

This guide explains the complete, official process for submitting **Sound Dictionaries** to the NVDA Add-on Store, how automated checks work, and how future updates are delivered seamlessly to NVDA users worldwide.

---

## 1. Overview of the NVDA Add-on Store

Starting with NVDA 2023.2, NV Access introduced the built-in **Add-on Store** (`NVDA Menu > Tools > Add-on Store`).
Submissions to the store are managed via the official GitHub repository:
👉 **[nvaccess/addon-datastore](https://github.com/nvaccess/addon-datastore)**

When you submit an add-on:
1. You fill out a simple GitHub issue form on `nvaccess/addon-datastore`.
2. A GitHub Actions bot automatically downloads your `.nvda-addon` file from your GitHub Release.
3. The bot extracts `manifest.ini`, computes the SHA256 checksum, verifies URL and metadata, and opens an automated Pull Request.
4. Automated scans (including VirusTotal) verify that the package is safe and free of malware.
5. Once approved, the add-on appears in NVDA's Add-on Store for all users worldwide!

---

## 2. Step-by-Step: Submitting Version 1.0.0

### Step 1: Confirm the GitHub Release
Ensure the GitHub Release for `v1.0.0` is published on:
`https://github.com/mehdimalakane/soundDictionaries/releases/tag/v1.0.0`

The downloadable release file URL is:
```
https://github.com/mehdimalakane/soundDictionaries/releases/download/v1.0.0/soundDictionaries-1.0.0.nvda-addon
```

### Step 2: Open the Add-on Registration Form
Go to the official registration issue template:
🔗 **[Add-on registration form on nvaccess/addon-datastore](https://github.com/nvaccess/addon-datastore/issues/new?template=registerAddon.yml)**

### Step 3: Fill Out the Form Fields

| Field | Value to Enter | Notes |
| :--- | :--- | :--- |
| **Download URL** | `https://github.com/mehdimalakane/soundDictionaries/releases/download/v1.0.0/soundDictionaries-1.0.0.nvda-addon` | Must start with `https` and end with `.nvda-addon`. |
| **Source URL** | `https://github.com/mehdimalakane/soundDictionaries` | Link to your public repository. |
| **Publisher** | `mehdi malakane` | Matches the author in `manifest.ini`. |
| **Channel** | `stable` | Select `stable` from the dropdown. |
| **License Name** | `GPL v2` | Standard GNU GPL v2. |
| **License URL** | `https://www.gnu.org/licenses/gpl-2.0.html` | Official GPL v2 link. |

### Step 4: Submit & Approval
1. Click **Submit new issue**.
2. An automated bot (`nvaccess-addon-datastore-bot`) will comment and open a Pull Request.
3. **First-time Submitter Approval:** Because `soundDictionaries` is a new add-on ID, an NV Access staff member will do a one-time verification to confirm you are the repository owner (`mehdimalakane`). This typically takes between a few days up to two weeks.
4. Once merged, `soundDictionaries` will be live in the Add-on Store!

---

## 3. How Future Updates Work (Automated Delivery Ecosystem)

Once `mehdi malakane` is approved as the maintainer of `soundDictionaries` in the Add-on Store, **future updates do not require manual review!** They are processed and published automatically.

### Automated Update Workflow:
```
  [1] Make code updates & bump version in manifest.ini (e.g. 1.0.1)
                            ↓
  [2] Push git tag (e.g. git tag v1.0.1 && git push origin v1.0.1)
                            ↓
  [3] GitHub Actions builds package, runs 45 tests, generates SHA256 & creates GitHub Release
                            ↓
  [4] Submit new version link on nvaccess/addon-datastore
                            ↓
  [5] Bot runs automated checks (VirusTotal, SHA256, manifest) and merges PR automatically
                            ↓
  [6] Users get an "Update available" notification inside NVDA and update with 1 click!
```

---

## 4. Checklist for Releases

Before publishing any new version:
- [ ] Version updated in `soundDictionaries/manifest.ini`.
- [ ] Changes documented in `soundDictionaries/doc/en/readme.html` and `README.md`.
- [ ] Full test suite passes: `python -m unittest discover tests`.
- [ ] Package built: `python build_addon.py`.
- [ ] Package validated: `python -m unittest tests/test_packageValidation.py`.
- [ ] Git tag pushed: `git tag vX.Y.Z && git push origin vX.Y.Z`.
- [ ] GitHub release verified with downloadable `.nvda-addon`.
