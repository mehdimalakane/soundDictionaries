# A part of Sound Dictionaries add-on for NVDA
# Copyright (C) 2026
# Licensed under GNU General Public License version 2 or later.

import re
from typing import Optional, Tuple

try:
	from speechDictHandler.types import EntryType, SpeechDictEntry
except ImportError:
	EntryType = None
	SpeechDictEntry = None

try:
	from logHandler import log
except ImportError:
	import logging
	log = logging.getLogger("soundDictionaries")


SOUND_TAG_REGEX = re.compile(r'<sound:([^>]+)>')

SOUND_MARKER_PREFIX = "\ue000SND"
SOUND_MARKER_SUFFIX = "\ue000"
# Matches both new hex markers and legacy markers for complete backward compatibility (case-insensitive)
SOUND_MARKER_REGEX = re.compile(r'(\ue000?SND[0-9a-fA-F]+\ue000?|\ue000?SOUND:[^\ue000]+\ue000?)', re.IGNORECASE)
SOUND_HEX_EXTRACT_REGEX = re.compile(r'^\ue000?SND([0-9a-fA-F]+)\ue000?$', re.IGNORECASE)
SOUND_LEGACY_EXTRACT_REGEX = re.compile(r'^\ue000?SOUND:([^\ue000]+)\ue000?$', re.IGNORECASE)

_originalEntrySub = None


def encodeSoundFilename(filename: str) -> str:
	"""Hex encode a sound filename to completely protect it from speech symbol processing."""
	return filename.strip().encode("utf-8").hex()


def decodeSoundFilename(hexStr: str) -> str:
	"""Decode a hex-encoded sound filename back to string."""
	try:
		return bytes.fromhex(hexStr.strip()).decode("utf-8")
	except Exception:
		return hexStr.strip()


def parseComment(rawComment: Optional[str]) -> Tuple[str, Optional[str]]:
	"""Extract user comment and sound filename from an entry's raw comment.

	:param rawComment: The raw comment string stored in the dictionary.
	:returns: (cleanUserComment, soundFileName or None)
	"""
	if not rawComment:
		return "", None

	rawComment = rawComment.strip()
	m = SOUND_TAG_REGEX.search(rawComment)
	if m:
		soundFileName = m.group(1).strip()
		cleanComment = SOUND_TAG_REGEX.sub("", rawComment).strip()
		return cleanComment, soundFileName

	return rawComment, None


def buildComment(userComment: str, soundFileName: Optional[str]) -> str:
	"""Construct the comment string storing the sound tag.

	:param userComment: The comment typed by the user.
	:param soundFileName: The sound filename, or None.
	:returns: Combined comment string for storage in .dic files.
	"""
	userComment = (userComment or "").strip()
	# Clean any existing sound tag in userComment
	userComment = SOUND_TAG_REGEX.sub("", userComment).strip()

	if soundFileName:
		soundFileName = soundFileName.strip()
		tag = f"<sound:{soundFileName}>"
		return f"{userComment} {tag}".strip() if userComment else tag

	return userComment


def makeSoundMarker(soundFileName: str) -> str:
	"""Create the Unicode PUA sound marker embedded into text during dictionary substitution.
	We encode the filename as hex so punctuation characters (such as '.' in '.wav' and spaces)
	cannot be stripped or corrupted by NVDA's symbol / punctuation processor.
	"""
	encoded = encodeSoundFilename(soundFileName)
	return f"\ue000SND{encoded}\ue000"


def prepareEntry(entry) -> None:
	"""Ensure an existing SpeechDictEntry has soundFileName and userComment attributes."""
	if not hasattr(entry, "soundFileName") or not hasattr(entry, "userComment"):
		cleanComment, soundFileName = parseComment(getattr(entry, "comment", ""))
		entry.userComment = cleanComment
		entry.soundFileName = soundFileName


from . import soundPlayer

_suppressSound = False


class suppressSound:
	"""Context manager to temporarily suppress sound playback (e.g. during GUI regex testing)."""

	def __enter__(self):
		global _suppressSound
		_suppressSound = True
		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		global _suppressSound
		_suppressSound = False


def entrySub(entry, text: str) -> str:
	"""Enhanced substitution method for SpeechDictEntry that plays sound and cleanly replaces text."""
	prepareEntry(entry)
	soundFile = getattr(entry, "soundFileName", None)

	isRegexp = (
		(EntryType and entry.type == EntryType.REGEXP)
		or entry.type == 1
		or getattr(entry.type, "value", None) == 1
	)

	if isRegexp:
		repl = entry.replacement
	else:
		repl = entry.replacement.replace("\\", "\\\\")

	# Check if this entry matches and has a sound file assigned
	if soundFile and not _suppressSound:
		try:
			if entry.compiled.search(text):
				soundPlayer.playSound(soundFile)
		except Exception as e:
			log.exception(f"Error triggering sound {soundFile} in entrySub: {e}")

	# Perform clean NVDA substitution without injecting any raw markers into the speech text
	if _originalEntrySub:
		return _originalEntrySub(entry, text)
	return entry.compiled.sub(repl, text)


def patchSpeechDictEntry() -> None:
	"""Hook SpeechDictEntry.sub to support sound injection."""
	global _originalEntrySub
	if not SpeechDictEntry or _originalEntrySub is not None:
		return

	_originalEntrySub = SpeechDictEntry.sub
	SpeechDictEntry.sub = entrySub
	log.debug("Patched SpeechDictEntry.sub for Sound Dictionaries")


def unpatchSpeechDictEntry() -> None:
	"""Restore original SpeechDictEntry.sub."""
	global _originalEntrySub
	if _originalEntrySub is not None and SpeechDictEntry:
		SpeechDictEntry.sub = _originalEntrySub
		_originalEntrySub = None
		log.debug("Restored SpeechDictEntry.sub")
