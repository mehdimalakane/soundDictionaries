# Sound Dictionaries for NVDA

[![License: GPL v2](https://img.shields.io/badge/License-GPL%20v2-blue.svg)](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html)
[![NVDA Compatibility](https://img.shields.io/badge/NVDA-2024.1%20--%202026.2+-green.svg)](https://www.nvaccess.org/)
[![Release](https://img.shields.io/github/v/release/mehdimalakane/soundDictionaries?include_prereleases)](https://github.com/mehdimalakane/soundDictionaries/releases)
[![Tests](https://img.shields.io/badge/Tests-45%20passed-brightgreen.svg)](https://github.com/mehdimalakane/soundDictionaries/actions)

**Sound Dictionaries** is an advanced NVDA add-on that brings **JAWS-style sound dictionary functionality** to the NVDA screen reader. It allows users to assign custom **WAV** or **MP3** audio file playback to specific words or phrases across all NVDA speech dictionaries (**Default**, **Voice**, and **Temporary**).

Developed by **mehdi malakane** (<mehdimalakane5@gmail.com>) and vibecoded using **Gemini 3.8 Flash** and **Antigravity**.

---

## Key Features

- **Deep Native NVDA Integration:** Seamlessly extends NVDA's existing speech dictionary interfaces without awkward external windows:
  - **Default Dictionary** (`NVDA+N > Preferences > Speech Dictionaries > Default dictionary`)
  - **Voice Dictionary** (`NVDA+N > Preferences > Speech Dictionaries > Voice dictionary`)
  - **Temporary Dictionary** (`NVDA+N > Preferences > Speech Dictionaries > Temporary dictionary`)
- **Dedicated Sound Column:** The dictionary entries table includes a dedicated **Sound** column showing the assigned audio file for each pattern.
- **Dual Audio Format Support:**
  - **WAV:** Played via NVDA's native WASAPI / `nvwave` engine with full audio ducking support.
  - **MP3:** Played asynchronously via Windows MCI with automatic handle management.
- **Self-Contained File Management:**
  - Selected audio files are safely copied to the add-on's internal `sounds/` directory.
  - Automatic content hashing prevents duplicate file storage.
  - File collisions (different files with the same filename) are cleanly disambiguated.
  - Moving or renaming your original audio files will never break your dictionary playback.
- **In-Dialog Audio Preview:** Test and preview sound files directly within the entry dialog before saving.
- **Flexible Playback Modes:**
  - **Sound Only (Mute & Play):** Leave the replacement field blank to mute the spoken phrase and play the sound instead.
  - **Sound + Replacement:** Play the sound and speak a replacement phrase.
  - **Full Regex Support:** Works seamlessly with Regular Expression patterns, word boundaries, and case sensitivity.
- **Instant Speech Cancellation:** Audio playback stops instantly when speech is silenced (e.g. pressing <kbd>Control</kbd> or <kbd>Shift</kbd>).
- **Clean Stream Architecture:** Audio cues trigger directly at match time with zero text tokens or markers injected into speech, completely preventing synthesizers from vocalizing internal codes.

---

## Installation

### Option 1: Direct Download (.nvda-addon)
1. Download the latest `soundDictionaries-1.0.0.nvda-addon` from the [Releases](https://github.com/mehdimalakane/soundDictionaries/releases) page.
2. In Windows Explorer, press <kbd>Enter</kbd> on the downloaded `.nvda-addon` file.
3. NVDA will ask: *"Are you sure you want to install this add-on?"* Press **Yes**.
4. Restart NVDA when prompted.

### Option 2: NVDA Add-on Store (Coming Soon)
Search for **Sound Dictionaries** directly in NVDA's built-in Add-on Store (`NVDA+N > Tools > Add-on Store`).

---

## How to Use

1. Open the NVDA menu with <kbd>NVDA+N</kbd>.
2. Navigate to **Preferences** > **Speech Dictionaries**.
3. Choose the dictionary you want to edit:
   - **Default dictionary:** Applies across all synthesizers and voices.
   - **Voice dictionary:** Applies only to the currently active voice.
   - **Temporary dictionary:** Resets when NVDA restarts.
4. Press **Add** (<kbd>Alt+A</kbd>) to create a new entry, or select an existing entry and press **Edit** (<kbd>Alt+E</kbd>).
5. In the entry dialog:
   - **Pattern (<kbd>Alt+P</kbd>):** Type the word, phrase, or regular expression to trigger on (e.g. `brb` or `:)` or `warning`).
   - **Replacement (<kbd>Alt+R</kbd>):**
     - Leave **empty** if you want the phrase replaced *exclusively* by the sound.
     - Enter text (e.g. `be right back`) if you want NVDA to speak replacement text while playing the sound.
   - **Browse... (<kbd>Alt+B</kbd>):** Pick any `.wav` or `.mp3` file from your computer.
   - **Play sound (<kbd>Alt+Y</kbd>):** Listen to the sound to make sure it is what you want.
   - **Clear sound (<kbd>Alt+D</kbd>):** Remove the sound assignment if you change your mind.
6. Press **OK** to save the entry, then press **OK** on the dictionary list to save changes to disk.

---

## Keyboard Shortcuts in Entry Dialog

| Shortcut | Action |
| :--- | :--- |
| <kbd>Alt+P</kbd> | Focus **Pattern** text field |
| <kbd>Alt+R</kbd> | Focus **Replacement** text field |
| <kbd>Alt+C</kbd> | Focus **Comment** text field |
| <kbd>Alt+A</kbd> | Focus **Selected audio file** text field |
| <kbd>Alt+B</kbd> | Open **Browse** dialog to choose audio file |
| <kbd>Alt+Y</kbd> | **Play sound** (listen to preview) |
| <kbd>Alt+D</kbd> | **Clear sound** (remove sound assignment) |
| <kbd>Alt+S</kbd> | Toggle **Case sensitive** checkbox |
| <kbd>Alt+T</kbd> | Focus **Type** radio buttons (Anywhere, Whole word, Regular expression) |
| <kbd>Enter</kbd> | Save entry (**OK**) |
| <kbd>Escape</kbd> | Cancel without saving |

---

## Architecture & Technical Design

The add-on is designed strictly in accordance with the NVDA Developer Guide and NVDA Add-on Development guidelines:

```
soundDictionaries/
├── manifest.ini                       # Add-on metadata and version compatibility
├── doc/                               # Bundled documentation in HTML and Markdown
│   └── en/
│       ├── readme.html
│       └── readme.md
├── globalPlugins/
│   └── soundDictionaries/
│       ├── __init__.py                # GlobalPlugin lifecycle & hook management
│       ├── dictionaryEntry.py         # Tag parser/formatter & clean substitution
│       ├── guiExtension.py            # Enhanced entry dialog & 6-column dictionary list
│       ├── soundPlayer.py             # Dual audio engine (WASAPI/nvwave & MCI) + ducking
│       ├── soundStorage.py            # Local sound repository, deduplication & cleanup
│       └── speechExtension.py         # Speech cancellation hook & dictionary loader
└── sounds/                            # Local storage for user audio files
```

### Persistence Specification
Sound assignments are saved directly inside NVDA's standard `.dic` files using a clean, native comment annotation tag:
```
#<sound:alert.wav> optional user comment
pattern	replacement	caseSensitive	type
```
- **Zero file corruption:** Standard NVDA instances without this add-on continue reading the dictionary without errors.
- **Portable:** When exporting or backing up your NVDA configuration profile, your dictionary rules remain intact.

---

## Automated Testing

Sound Dictionaries comes with a comprehensive, robust test suite containing **45 automated tests**:

```bash
# Run all unit and integration tests
python -m unittest discover tests
```

- **`test_soundStorage.py` (7 tests):** Directory resolution, file copying, deduplication, collision handling, path resolution, and orphan cleanup.
- **`test_soundPlayer.py` (5 tests):** WAV/MP3 routing, error resilience, playback debouncing, and cancellation hook registration.
- **`test_dictionaryEntry.py` (11 tests):** Tag extraction, clean substitution, empty replacement, regex capture groups, case sensitivity, and zero-marker safety verification.
- **`test_speechExtension.py` (9 tests):** Speech sequence splitting, legacy marker fallbacks, and command dispatching.
- **`test_guiExtension.py` (8 tests):** GUI controls, tab order accessibility, preview path preservation, automatic file copying on save, and `SpeechDictEntry` integration.
- **`test_manifestValidation.py` (2 tests):** `manifest.ini` specification compliance.
- **`test_packageValidation.py` (2 tests):** `.nvda-addon` bundle structure, ZIP validity, root manifest, and cache elimination.
- **`test_integration.py` (1 test):** Full end-to-end add-on lifecycle simulation.

---

## Building from Source

To package the add-on into a distributable `.nvda-addon` file:

```bash
python build_addon.py
```

This will automatically create `soundDictionaries-<version>.nvda-addon` in the root directory.

---

## 📚 Maintainer & Developer Documentation

- **[Maintainer & Developer Comprehensive Guide](docs/MAINTAINERS_GUIDE.md):** Detailed guide covering architecture, audio engine, CI/CD, and release management.
- **[NVDA Add-on Store Submission Guide](docs/addon_store_submission.md):** Complete step-by-step instructions for publishing and updating on the official NVDA Add-on Store.

---

## Author & Credits

- **Author:** **mehdi malakane** (<mehdimalakane5@gmail.com>)
- **GitHub:** [@mehdimalakane](https://github.com/mehdimalakane)
- **Development Tooling:** Vibecoded using **Gemini 3.8 Flash** and **Antigravity**.

---

## License

This project is licensed under the **GNU General Public License v2.0 (GPLv2)** - see the [LICENSE](LICENSE) file for details.
