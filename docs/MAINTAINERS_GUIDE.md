# Sound Dictionaries: Maintainer & Developer Comprehensive Guide 📘

This document is the **definitive technical reference and operations manual** for the **Sound Dictionaries** NVDA add-on. Whether you are returning to this codebase after months or years, or a new developer is contributing to the project, this guide contains **everything required** to understand, develop, test, release, and distribute the add-on.

---

## 📑 Table of Contents
1. [Project Overview & Key Metadata](#1-project-overview--key-metadata)
2. [Deep Architecture & How the Add-on Works](#2-deep-architecture--how-the-add-on-works)
3. [Local Development & Environment Setup](#3-local-development--environment-setup)
4. [Testing & Quality Assurance](#4-testing--quality-assurance)
5. [Step-by-Step Git & GitHub Release Workflow](#5-step-by-step-git--github-release-workflow)
6. [NVDA Add-on Store Submission & Updating Process](#6-nvda-add-on-store-submission--updating-process)
7. [Automated CI/CD Workflows Explained](#7-automated-cicd-workflows-explained)
8. [Critical Engineering Rules & Pitfalls to Avoid](#8-critical-engineering-rules--pitfalls-to-avoid)

---

## 1. Project Overview & Key Metadata

- **Add-on Name (Internal ID):** `soundDictionaries`
- **Summary:** Sound Dictionaries
- **Author:** `mehdi malakane <mehdimalakane5@gmail.com>`
- **GitHub Repository:** [https://github.com/mehdimalakane/soundDictionaries](https://github.com/mehdimalakane/soundDictionaries)
- **License:** GNU General Public License v2.0 (GPLv2)
- **Minimum Supported NVDA Version:** `2024.1.0`
- **Last Tested NVDA Version:** `2026.2.0`
- **Development Tooling:** Vibecoded using **Gemini 3.8 Flash** and **Antigravity**.

---

## 2. Deep Architecture & How the Add-on Works

The add-on integrates directly into NVDA's core speech and dictionary subsystem without spawning standalone GUI windows. It consists of 5 modular components inside `soundDictionaries/globalPlugins/soundDictionaries/`:

```
soundDictionaries/
├── manifest.ini                       # Add-on metadata, versions, and author
├── doc/en/                            # Documentation (readme.html and readme.md)
├── sounds/                            # Storage folder for user audio files (.wav, .mp3)
└── globalPlugins/soundDictionaries/
    ├── __init__.py                    # GlobalPlugin lifecycle (initialize/terminate)
    ├── dictionaryEntry.py             # Sound tags parsing, formatting & clean substitution
    ├── guiExtension.py                # Enhances NVDA dictionary dialogs & 6-column list
    ├── soundPlayer.py                 # Audio player: WAV (WASAPI/nvwave) & MP3 (MCI)
    ├── soundStorage.py                # Sound file copying, deduplication, & path resolution
    └── speechExtension.py             # Speech cancellation hook & dictionary loader
```

### 2.1 Native Persistence Specification (`.dic` Files)
NVDA's native dictionary files (`default.dic`, `voiceDicts.dic`, `temporary.dic`) use a strict 4-column tab-separated format:
```
#optional comment
pattern	replacement	caseSensitive	type
```
> [!IMPORTANT]
> **Never modify the 4 tab columns!** Adding a 5th column would break standard NVDA parsing if the add-on is disabled.
> Instead, sound references are encoded cleanly in the comment line:
> `#<sound:filename.ext> Optional user comment text`
>
> When the add-on is active:
> - `dictionaryEntry.parseComment()` extracts `soundFileName` and returns the clean `userComment`.
> - Screen reader users only hear their own clean comment in the Comment field and the sound in the Sound column.

### 2.2 Direct Execution & Clean Speech Stream Architecture
Early prototypes used unicode tokens (like `\ue000SND...\ue000`) injected into the speech sequence. However, when navigating with review cursors or using synthesizers like Vocalizer Expressive 2, raw tokens could be voiced aloud if index callbacks stalled on empty text.

**The Current Solution (Direct Clean Execution):**
1. `SpeechDictEntry.sub(text)` is hooked by `dictionaryEntry.entrySub`.
2. When the pattern matches:
   - `soundPlayer.playSound(soundFile)` is invoked immediately and asynchronously.
   - The method returns the clean replacement text (`entry.replacement`), or empty string `""` if replacement is blank.
3. **Zero tokens or markers are ever placed in the text stream.**
4. No speech synthesizer can ever vocalize codes or symbols because none exist in the text!

### 2.3 Audio Engine (`soundPlayer.py`)
- **WAV Files:** Played through NVDA's internal `nvwave.playWaveFile(filePath, asynchronous=True)`. This automatically routes through the user's selected NVDA audio output device and respects audio ducking.
- **MP3 Files:** Played via Windows Multi-Media MCI (`winmm.mciSendStringW`). Uses 8.3 short paths (`GetShortPathNameW`) to guarantee 100% reliability with unicode paths and spaces.
- **Audio Debounce:** An 80ms deduplication filter prevents audio double-firing when NVDA processes repeated caret navigation events.
- **Cancellation:** Listens to `speech.extensions.speechCanceled`. Pressing <kbd>Control</kbd> or <kbd>Shift</kbd> silences playing audio immediately.

### 2.4 Sound Storage & Deduplication (`soundStorage.py`)
- User audio files are copied to the add-on's `sounds/` directory.
- SHA256 content hashing guarantees that assigning the same sound file multiple times reuses the existing copy without duplicating disk space.
- Name collisions (e.g. two different files named `bell.wav`) are automatically resolved by appending a counter (`bell_1.wav`).

---

## 3. Local Development & Environment Setup

### Prerequisites
- Windows 10 or 11
- Python 3.11, 3.12, or 3.13 installed
- Git
- GitHub CLI (`gh`)
- NVDA installed (2024.1 or later)

### Directory Layout
```
c:\Users\USER\Documents\nvda dic sound\
├── .github/                           # Workflows (ci.yml, release.yml) and issue templates
├── docs/                              # Detailed guides (this guide, store submission guide)
├── soundDictionaries/                 # Add-on source files
├── tests/                             # Automated test suite (45 unit/integration tests)
├── build_addon.py                     # Official packager script
├── README.md                          # Repository root README
└── LICENSE                            # GPL v2.0 license
```

---

## 4. Testing & Quality Assurance

The repository features **45 automated tests** covering 100% of core components:

```bash
# Run the entire test suite locally
python -m unittest discover tests
```

### Test Breakdown:
| Test File | Coverage |
| :--- | :--- |
| `tests/test_soundStorage.py` | Sound copying, path resolution, deduplication, collision renaming, unreferenced deletion. |
| `tests/test_soundPlayer.py` | WAV vs MP3 format routing, debouncing, error handling, cancellation registration. |
| `tests/test_dictionaryEntry.py` | Tag parsing, clean substitution, empty replacement, regex capture groups, case sensitivity, zero-marker safety. |
| `tests/test_speechExtension.py` | Legacy marker backward compatibility, speech sequence processing, command dispatching. |
| `tests/test_guiExtension.py` | GUI dialogs, tab ordering, browse path preservation, automatic file copying on OK, `SpeechDictEntry` integration. |
| `tests/test_manifestValidation.py` | Validates `manifest.ini` schema, versions, and required fields. |
| `tests/test_packageValidation.py` | Auto-builds and validates `.nvda-addon` ZIP structure, files, and manifest integrity. |
| `tests/test_integration.py` | Full end-to-end simulation from GUI entry creation to sound playback. |

> [!NOTE]
> When tests run in a headless environment without `wxPython` (such as GitHub Actions runners), the GUI tests skip gracefully while all 37 core logic tests execute and validate.

---

## 5. Step-by-Step Git & GitHub Release Workflow

Whenever you develop new features, fix bugs, or release a new version, follow this checklist in exact order:

### Step 1: Implement Code Changes
Make your changes in `soundDictionaries/globalPlugins/soundDictionaries/`.

### Step 2: Bump the Version
Edit `soundDictionaries/manifest.ini`:
```ini
version = "1.0.1"  # Or your new version number
```
Also update documentation in `soundDictionaries/doc/en/readme.html` and `README.md` to reflect what changed.

### Step 3: Run the Test Suite Locally
```bash
python -m unittest discover tests
```
Ensure all tests pass.

### Step 4: Build the Add-on Locally
```bash
python build_addon.py
```
This produces `soundDictionaries-<version>.nvda-addon`.

### Step 5: Test Locally in NVDA
Install the built `.nvda-addon` file in your installed NVDA to perform real manual verification. Check `%TEMP%\nvda.log` to confirm zero exceptions.

### Step 6: Commit and Push to GitHub
```bash
git add .
git commit -m "Describe your changes clearly"
git push origin main
```
The GitHub Actions **CI** workflow will trigger automatically and run the test matrix across Python 3.11, 3.12, and 3.13.

### Step 7: Create and Push a Version Tag
```bash
git tag -a v1.0.1 -m "Release v1.0.1"
git push origin v1.0.1
```

### What Happens Next (Automated):
The `.github/workflows/release.yml` GitHub Actions pipeline will:
1. Run all 45 automated tests on a clean runner.
2. Build the `.nvda-addon` package.
3. Compute the SHA256 checksum.
4. Create an official **GitHub Release** with the `.nvda-addon` file attached and release notes populated!

---

## 6. NVDA Add-on Store Submission & Updating Process

The official NVDA Add-on Store is hosted at:
👉 **[nvaccess/addon-datastore](https://github.com/nvaccess/addon-datastore)**

### 6.1 Initial Submission (Version 1.0.0)
1. Open the [Add-on Registration Form on nvaccess/addon-datastore](https://github.com/nvaccess/addon-datastore/issues/new?template=registerAddon.yml).
2. Enter the following values:
   - **Download URL:** `https://github.com/mehdimalakane/soundDictionaries/releases/download/v1.0.0/soundDictionaries-1.0.0.nvda-addon`
   - **Source URL:** `https://github.com/mehdimalakane/soundDictionaries`
   - **Publisher:** `mehdi malakane`
   - **Channel:** `stable`
   - **License Name:** `GPL v2`
   - **License URL:** `https://www.gnu.org/licenses/gpl-2.0.html`
3. Click **Submit new issue**.
4. The automated bot (`nvaccess-addon-datastore-bot`) downloads your release asset, validates the SHA256, runs VirusTotal scans, and generates a Pull Request.
5. An NV Access staff member performs a one-time verification approving `mehdimalakane` as the official maintainer of `soundDictionaries`.

### 6.2 Submitting Future Updates (v1.0.1, v1.1.0, etc.)
> [!TIP]
> **Subsequent updates do not require manual review!**
> Once approved as a submitter for `soundDictionaries`, future releases are automated:
1. Push your new version tag (e.g. `v1.0.1`), allowing GitHub Actions to publish the release asset.
2. Open the [Add-on Registration Form](https://github.com/nvaccess/addon-datastore/issues/new?template=registerAddon.yml) and provide the new Download URL (e.g. `.../releases/download/v1.0.1/soundDictionaries-1.0.1.nvda-addon`).
3. The automated bot validates the release, and **automatically merges the Pull Request without human review delay**.
4. NVDA users worldwide receive the update in NVDA's built-in Add-on Store!

---

## 7. Automated CI/CD Workflows Explained

The project uses two GitHub Actions workflows located in `.github/workflows/`:

### 1. `ci.yml` (Continuous Integration)
- **Triggers:** On every `push` and `pull_request` targeting `main`.
- **Matrix:** Runs on `windows-latest` across Python 3.11, 3.12, and 3.13.
- **Actions:**
  - Installs dependencies (`configobj`).
  - Builds the add-on bundle (`python build_addon.py`).
  - Executes full test suite (`python -m unittest discover tests`).

### 2. `release.yml` (Automated Releases)
- **Triggers:** On pushing any git tag matching `v*`.
- **Actions:**
  - Builds the package.
  - Computes the lowercase SHA256 checksum.
  - Validates archive structure and manifest.
  - Creates the GitHub Release attaching the `.nvda-addon` asset.
  - Formats release notes containing the exact submission URL and metadata.

---

## 8. Critical Engineering Rules & Pitfalls to Avoid

When maintaining or extending this codebase, adhere strictly to these rules:

1. **Lazy Type Annotations (`from __future__ import annotations`):**
   In GUI modules like `guiExtension.py`, always include `from __future__ import annotations` and avoid typing event parameters with `wx.CommandEvent` at class level without a fallback. In headless environments where `wx is None`, class-level evaluation of `wx.CommandEvent` will raise an `AttributeError`.
2. **Never Inject Tokens into Synthesizer Text:**
   Keep the speech substitution clean in `dictionaryEntry.entrySub`. Trigger sounds directly at match time via `soundPlayer.playSound()` and return clean text to NVDA.
3. **Preserve Tab Separation in `.dic`:**
   NVDA's dictionary parser strictly expects 4 tab-separated fields. Never add extra tabs. Always store sound metadata in comment tags: `#<sound:filename.ext>`.
4. **Use Short Path Names for MCI (`soundPlayer.py`):**
   When playing MP3s via MCI, always resolve to Windows 8.3 short paths (`GetShortPathNameW`). MCI will fail with unicode characters or spaces if full paths are passed directly.
5. **Always Bump `lastTestedNVDAVersion` when NVDA Updates:**
   Each year when NV Access releases a new major NVDA version (e.g. `2027.1`), test the add-on against the new version, update `lastTestedNVDAVersion` in `manifest.ini`, and release a compatibility bump.

---
*Guide maintained by **mehdi malakane** (<mehdimalakane5@gmail.com>).*
