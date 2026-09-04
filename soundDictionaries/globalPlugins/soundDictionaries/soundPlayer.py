# A part of Sound Dictionaries add-on for NVDA
# Copyright (C) 2026
# Licensed under GNU General Public License version 2 or later.

import os
import time
import ctypes
import threading
from typing import Optional

try:
	import nvwave
except ImportError:
	nvwave = None

try:
	import speech
except ImportError:
	speech = None

try:
	import winsound
except ImportError:
	winsound = None

try:
	from logHandler import log
except ImportError:
	import logging
	log = logging.getLogger("soundDictionaries")

from . import soundStorage

_winmm = None
try:
	_winmm = ctypes.windll.winmm
except Exception as e:
	log.debugWarning(f"Could not load winmm.dll: {e}")

_mciLock = threading.Lock()
_currentMciAlias: Optional[str] = None
_cancellationRegistered = False


def _getShortPath(path: str) -> str:
	"""Return 8.3 short path name if possible for maximum MCI compatibility."""
	try:
		buf = ctypes.create_unicode_buffer(500)
		res = ctypes.windll.kernel32.GetShortPathNameW(path, buf, 500)
		if res > 0:
			return buf.value
	except Exception:
		pass
	return path


def playMp3(filePath: str) -> bool:
	"""Play an MP3 file asynchronously via Windows MCI.

	:param filePath: Absolute path to the MP3 file.
	:returns: True if command succeeded, False otherwise.
	"""
	global _currentMciAlias
	if not _winmm:
		log.warning("winmm.dll is not available for MP3 playback")
		return False

	mciSendString = _winmm.mciSendStringW
	with _mciLock:
		try:
			alias = "nvdadic_audio"
			# Stop and close any previous instance
			mciSendString(f'close "{alias}"', None, 0, 0)
			_currentMciAlias = None

			targetPath = _getShortPath(filePath)
			cmdOpen = f'open "{targetPath}" type mpegvideo alias "{alias}"'
			ret = mciSendString(cmdOpen, None, 0, 0)
			if ret != 0:
				# Fallback: attempt without explicit device type
				cmdOpen = f'open "{targetPath}" alias "{alias}"'
				ret = mciSendString(cmdOpen, None, 0, 0)

			if ret != 0:
				log.warning(f"MCI open failed for {filePath} (error code {ret})")
				return False

			retPlay = mciSendString(f'play "{alias}" from 0', None, 0, 0)
			if retPlay != 0:
				log.warning(f"MCI play failed for {filePath} (error code {retPlay})")
				mciSendString(f'close "{alias}"', None, 0, 0)
				return False

			_currentMciAlias = alias
			return True
		except Exception as e:
			log.exception(f"Error playing MP3 file {filePath}: {e}")
			return False


def playWav(filePath: str) -> bool:
	"""Play a WAV file asynchronously using NVDA's nvwave or winsound fallback.

	:param filePath: Absolute path to the WAV file.
	:returns: True if playback started successfully, False otherwise.
	"""
	# Priority 1: Use NVDA's nvwave if available (WASAPI, output device, ducking)
	if nvwave:
		try:
			nvwave.playWaveFile(filePath, asynchronous=True)
			return True
		except Exception as e:
			log.debugWarning(f"nvwave failed to play {filePath}: {e}. Trying fallback.")

	# Priority 2: Standard winsound async playback
	if winsound:
		try:
			winsound.PlaySound(filePath, winsound.SND_FILENAME | winsound.SND_ASYNC)
			return True
		except Exception as e:
			log.debugWarning(f"winsound failed to play {filePath}: {e}. Trying MCI.")

	# Priority 3: MCI fallback
	return playMp3(filePath)


_lastPlayedSound = None
_lastPlayedTime = 0.0


def playSound(soundRef: str) -> bool:
	"""Play an audio file (WAV or MP3).

	:param soundRef: Filename in the add-on's sounds directory or absolute path.
	:returns: True if playback started, False otherwise.
	"""
	global _lastPlayedSound, _lastPlayedTime
	if not soundRef:
		return False

	now = time.time()
	# Debounce identical sound triggers within 60ms to prevent duplicate rapid fires
	if soundRef == _lastPlayedSound and (now - _lastPlayedTime) < 0.06:
		return True

	resolved = soundStorage.resolveSoundPath(soundRef)
	if not resolved:
		log.warning(f"Audio file could not be resolved: {soundRef}")
		return False

	_lastPlayedSound = soundRef
	_lastPlayedTime = now

	base, ext = os.path.splitext(resolved)
	extLower = ext.lower()

	if extLower == ".wav":
		return playWav(resolved)
	elif extLower == ".mp3":
		return playMp3(resolved)
	else:
		log.warning(f"Unsupported audio format for playback: {resolved}")
		return False


def stopAudio() -> None:
	"""Stop any currently playing audio immediately."""
	global _currentMciAlias

	# Stop MCI audio
	if _winmm:
		with _mciLock:
			if _currentMciAlias:
				try:
					_winmm.mciSendStringW(f'stop "{_currentMciAlias}"', None, 0, 0)
					_winmm.mciSendStringW(f'close "{_currentMciAlias}"', None, 0, 0)
				except Exception:
					pass
				_currentMciAlias = None

	# Stop winsound
	if winsound:
		try:
			winsound.PlaySound(None, winsound.SND_PURGE)
		except Exception:
			pass

	# Stop nvwave file player
	if nvwave and getattr(nvwave, "fileWavePlayer", None):
		try:
			nvwave.fileWavePlayer.stop()
		except Exception:
			pass


def _onSpeechCanceled(*args, **kwargs) -> None:
	"""Callback triggered when NVDA speech is canceled."""
	stopAudio()


def registerCancellationHook() -> None:
	"""Register audio stop handler with NVDA's speech cancellation extension points."""
	global _cancellationRegistered
	if _cancellationRegistered:
		return
	if speech:
		try:
			if hasattr(speech, "speechCanceled") and hasattr(speech.speechCanceled, "register"):
				speech.speechCanceled.register(_onSpeechCanceled)
			if hasattr(speech, "pre_speechCanceled") and hasattr(speech.pre_speechCanceled, "register"):
				speech.pre_speechCanceled.register(_onSpeechCanceled)
			_cancellationRegistered = True
			log.debug("Registered soundDictionaries cancellation hooks")
		except Exception as e:
			log.warning(f"Could not register speech cancellation hook: {e}")


def unregisterCancellationHook() -> None:
	"""Unregister audio stop handler."""
	global _cancellationRegistered
	stopAudio()
	if not _cancellationRegistered:
		return
	if speech:
		try:
			if hasattr(speech, "speechCanceled") and hasattr(speech.speechCanceled, "unregister"):
				speech.speechCanceled.unregister(_onSpeechCanceled)
			if hasattr(speech, "pre_speechCanceled") and hasattr(speech.pre_speechCanceled, "unregister"):
				speech.pre_speechCanceled.unregister(_onSpeechCanceled)
		except Exception:
			pass
	_cancellationRegistered = False
