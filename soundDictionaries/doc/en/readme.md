# Sound Dictionaries for NVDA

**Author:** mehdi malakane (<mehdimalakane5@gmail.com>)  
**Repository:** https://github.com/mehdimalakane/soundDictionaries  
**Development:** Vibecoded using **Gemini 3.8 Flash** and **Antigravity**  
**License:** GNU General Public License v2.0  

---

**Sound Dictionaries** is an NVDA add-on that enables screen reader users to assign custom WAV or MP3 audio playback to specific phrases across all speech dictionaries (Default, Voice, and Temporary). Similar to JAWS dictionary sound assignments, phrases can trigger audio cues with or without replacement text.

## Features

- **Deep Native Integration:** Fully embedded within NVDA's built-in speech dictionary management interfaces:
  - Default Dictionary
  - Voice Dictionary
  - Temporary Dictionary
- **Dual Format Support:** Supports both uncompressed .wav (using native WASAPI/nvwave with audio ducking) and .mp3 audio files.
- **Dedicated Sound Column:** The dictionary list features a dedicated 'Sound' column showing assigned sound files at a glance.
- **Self-Contained Storage:** Chosen audio files are automatically copied to the add-on's internal sounds/ directory, preventing broken links.
- **In-Dialog Audio Preview:** Test and preview sound playback directly in the entry dialog before saving.
- **Flexible Playback:**
  - *Sound Only:* Leave replacement empty to replace the spoken phrase entirely with sound.
  - *Sound + Replacement:* Play sound and speak replacement text simultaneously.
- **Speech Synchronization & Cancellation:** Audio playback stops immediately whenever speech is cancelled (e.g. pressing Control or Shift).
- **Clean Execution:** No tokens, markers, or hex codes are voiced aloud by the synthesizer.

## How to Use

1. Open NVDA Menu (NVDA+N) > **Preferences** > **Speech Dictionaries**.
2. Choose **Default dictionary**, **Voice dictionary**, or **Temporary dictionary**.
3. Press **Add** (Alt+A) or select an existing entry and press **Edit** (Alt+E).
4. In the dialog:
   - **Pattern:** Enter the word, phrase, or regular expression to match.
   - **Replacement:** Enter replacement text, or leave blank for sound-only.
   - **Browse... (Alt+B):** Select a .wav or .mp3 audio file.
   - **Play sound (Alt+Y):** Preview the selected audio file.
   - **Clear sound (Alt+D):** Clear the assigned sound file.
5. Click **OK** to save.

## Keyboard Shortcuts in Entry Dialog

- Alt+P: Pattern field
- Alt+R: Replacement field
- Alt+C: Comment field
- Alt+A: Selected audio file path
- Alt+B: Browse for sound file
- Alt+Y: Play/preview sound
- Alt+D: Clear assigned sound
- Alt+S: Case sensitive checkbox
- Alt+T: Match type (Anywhere, Whole word, Regular expression)

## Author & Support

Developed by **mehdi malakane** (<mehdimalakane5@gmail.com>).  
Vibecoded using **Gemini 3.8 Flash** and **Antigravity**.  

GitHub Repository: https://github.com/mehdimalakane/soundDictionaries
