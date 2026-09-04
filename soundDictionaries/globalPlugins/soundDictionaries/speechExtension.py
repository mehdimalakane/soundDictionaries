# A part of Sound Dictionaries add-on for NVDA
# Copyright (C) 2026
# Licensed under GNU General Public License version 2 or later.

from typing import Optional, List, Any

try:
	import speech
	from speech.commands import BaseCallbackCommand
	from speech.manager import SpeechManager
except ImportError:
	speech = None
	BaseCallbackCommand = object
	SpeechManager = None

try:
	import speechDictHandler
	from speechDictHandler.types import SpeechDict
except ImportError:
	speechDictHandler = None
	SpeechDict = None

try:
	from logHandler import log
except ImportError:
	import logging
	log = logging.getLogger("soundDictionaries")

from . import soundPlayer
from . import soundStorage
from .dictionaryEntry import (
	SOUND_MARKER_REGEX,
	SOUND_HEX_EXTRACT_REGEX,
	SOUND_LEGACY_EXTRACT_REGEX,
	decodeSoundFilename,
	prepareEntry,
	patchSpeechDictEntry,
	unpatchSpeechDictEntry,
)

_originalSpeechManagerSpeak = None
_originalSpeechDictLoad = None


class SoundCommand(BaseCallbackCommand):
	"""Speech command that plays an audio file when reached during speech synthesis."""

	def __init__(self, soundFileName: str, soundPath: str):
		super().__init__()
		self.soundFileName = soundFileName
		self.soundPath = soundPath

	def run(self) -> None:
		"""Execute sound playback when synthesis reaches this point."""
		try:
			soundPlayer.playSound(self.soundPath)
		except Exception as e:
			log.exception(f"Error executing SoundCommand for {self.soundPath}: {e}")

	def __repr__(self) -> str:
		return f"SoundCommand({self.soundFileName!r})"


def splitSpeechSequenceWithSounds(speechSequence: List[Any]) -> List[Any]:
	"""Scan speech sequence for sound markers and split into text chunks and SoundCommands."""
	if not speechSequence:
		return speechSequence

	newSequence = []
	for item in speechSequence:
		if isinstance(item, str) and SOUND_MARKER_REGEX.search(item):
			parts = SOUND_MARKER_REGEX.split(item)
			for part in parts:
				if not part:
					continue
				mHex = SOUND_HEX_EXTRACT_REGEX.match(part)
				if mHex:
					soundFileName = decodeSoundFilename(mHex.group(1))
				else:
					mLeg = SOUND_LEGACY_EXTRACT_REGEX.match(part)
					soundFileName = mLeg.group(1).strip() if mLeg else None

				if soundFileName:
					soundPath = soundStorage.resolveSoundPath(soundFileName)
					if not soundPath:
						# Fallback 1: check if symbol processor replaced dot with space, e.g. "bell wav" -> "bell.wav"
						if soundFileName.endswith(" wav"):
							candidate = soundStorage.resolveSoundPath(soundFileName[:-4] + ".wav")
							if candidate:
								soundPath = candidate
								soundFileName = soundFileName[:-4] + ".wav"
						elif soundFileName.endswith(" mp3"):
							candidate = soundStorage.resolveSoundPath(soundFileName[:-4] + ".mp3")
							if candidate:
								soundPath = candidate
								soundFileName = soundFileName[:-4] + ".mp3"

					if not soundPath:
						# Fallback 2: check if extension was dropped entirely
						for ext in (".wav", ".mp3"):
							candidate = soundStorage.resolveSoundPath(soundFileName + ext)
							if candidate:
								soundPath = candidate
								soundFileName += ext
								break

					if soundPath:
						newSequence.append(SoundCommand(soundFileName, soundPath))
					else:
						log.warning(f"Sound file not found for speech command: {soundFileName}")
				else:
					newSequence.append(part)
		else:
			newSequence.append(item)

	return newSequence


def speechManagerSpeak(self, speechSequence: List[Any], *args, **kwargs) -> Any:
	"""Wrapped SpeechManager.speak to inject SoundCommands."""
	try:
		speechSequence = splitSpeechSequenceWithSounds(speechSequence)
	except Exception as e:
		log.exception(f"Error processing speech sequence with sound markers: {e}")

	# Special case: if the sequence contains ONLY SoundCommands (or whitespace),
	# execute them immediately to avoid any synth driver stalls on textless utterances.
	if speechSequence and all(
		isinstance(item, SoundCommand) or (isinstance(item, str) and not item.strip())
		for item in speechSequence
	):
		for cmd in speechSequence:
			if isinstance(cmd, SoundCommand):
				cmd.run()
		return None

	if _originalSpeechManagerSpeak:
		return _originalSpeechManagerSpeak(self, speechSequence, *args, **kwargs)


def prepareAllLoadedDictionaries() -> None:
	"""Scan all currently loaded speech dictionaries and prepare their entries."""
	if not speechDictHandler:
		return

	try:
		defs = speechDictHandler.definitions._speechDictDefinitions
		for d in defs:
			dictionary = getattr(d, "dictionary", None)
			if dictionary:
				for entry in dictionary:
					prepareEntry(entry)
	except Exception as e:
		log.debugWarning(f"Error preparing loaded dictionaries: {e}")


def speechDictLoad(self, fileName: str, *args, **kwargs) -> Any:
	"""Wrapped SpeechDict.load to automatically prepare entries when dictionaries are loaded from disk."""
	res = _originalSpeechDictLoad(self, fileName, *args, **kwargs)
	try:
		for entry in self:
			prepareEntry(entry)
	except Exception as e:
		log.debugWarning(f"Error preparing newly loaded dictionary {fileName}: {e}")
	return res


def initializeSpeechHooks() -> None:
	"""Initialize speech system hooks."""
	global _originalSpeechManagerSpeak, _originalSpeechDictLoad

	# Hook SpeechDictEntry substitution
	patchSpeechDictEntry()

	# Prepare currently loaded dictionaries
	prepareAllLoadedDictionaries()

	# Hook SpeechDict.load
	if SpeechDict and _originalSpeechDictLoad is None:
		_originalSpeechDictLoad = SpeechDict.load
		SpeechDict.load = speechDictLoad
		log.debug("Hooked SpeechDict.load for Sound Dictionaries")

	# Hook SpeechManager.speak
	if SpeechManager and _originalSpeechManagerSpeak is None:
		_originalSpeechManagerSpeak = SpeechManager.speak
		SpeechManager.speak = speechManagerSpeak
		log.debug("Hooked SpeechManager.speak for Sound Dictionaries")

	# Register speech cancellation hook
	soundPlayer.registerCancellationHook()


def terminateSpeechHooks() -> None:
	"""Clean up and restore all speech system hooks."""
	global _originalSpeechManagerSpeak, _originalSpeechDictLoad

	# Restore SpeechDictEntry.sub
	unpatchSpeechDictEntry()

	# Restore SpeechDict.load
	if _originalSpeechDictLoad is not None and SpeechDict:
		SpeechDict.load = _originalSpeechDictLoad
		_originalSpeechDictLoad = None
		log.debug("Restored SpeechDict.load")

	# Restore SpeechManager.speak
	if _originalSpeechManagerSpeak is not None and SpeechManager:
		SpeechManager.speak = _originalSpeechManagerSpeak
		_originalSpeechManagerSpeak = None
		log.debug("Restored SpeechManager.speak")

	# Unregister speech cancellation hook
	soundPlayer.unregisterCancellationHook()
