# A part of Sound Dictionaries add-on for NVDA
# Copyright (C) 2026
# Licensed under GNU General Public License version 2 or later.

import os
import re
import shutil
import hashlib
from typing import Optional

try:
	import addonHandler
except ImportError:
	addonHandler = None

try:
	from logHandler import log
except ImportError:
	import logging
	log = logging.getLogger("soundDictionaries")

SUPPORTED_EXTENSIONS = {".wav", ".mp3"}


def getAddonDir() -> str:
	"""Return the root directory of this add-on."""
	if addonHandler:
		try:
			addon = addonHandler.getCodeAddon()
			if addon and getattr(addon, "path", None) and os.path.isdir(addon.path):
				return os.path.abspath(addon.path)
		except Exception:
			pass
	# Fallback: calculate relative to this file: <addon_root>/globalPlugins/soundDictionaries/soundStorage.py
	return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def getSoundsDir() -> str:
	"""Return the path to the sounds directory inside the add-on folder, creating it if needed."""
	soundsDir = os.path.join(getAddonDir(), "sounds")
	os.makedirs(soundsDir, exist_ok=True)
	return soundsDir


def _getFileHash(filePath: str) -> str:
	"""Calculate SHA256 hash of a file for duplicate detection."""
	h = hashlib.sha256()
	with open(filePath, "rb") as f:
		while chunk := f.read(65536):
			h.update(chunk)
	return h.hexdigest()


def copySoundFile(sourcePath: str) -> str:
	"""Copy a WAV or MP3 audio file into the add-on's sounds directory.

	:param sourcePath: Path to the audio file on the user's system.
	:returns: The base filename stored in the sounds directory.
	:raises FileNotFoundError: If sourcePath does not exist.
	:raises ValueError: If the file format is not supported (.wav or .mp3).
	"""
	sourcePath = os.path.abspath(sourcePath)
	if not os.path.isfile(sourcePath):
		raise FileNotFoundError(f"Audio file not found: {sourcePath}")

	base, ext = os.path.splitext(sourcePath)
	extLower = ext.lower()
	if extLower not in SUPPORTED_EXTENSIONS:
		raise ValueError(f"Unsupported audio format '{ext}'. Only WAV and MP3 files are supported.")

	soundsDir = getSoundsDir()

	# If the file is already inside the add-on's sounds directory, return its basename
	if os.path.dirname(sourcePath) == soundsDir:
		return os.path.basename(sourcePath)

	baseName = os.path.splitext(os.path.basename(sourcePath))[0]
	safeBaseName = re.sub(r'[\\/*?:"<>|]', "_", baseName).strip()
	if not safeBaseName:
		safeBaseName = "audio"

	sourceHash = _getFileHash(sourcePath)
	destFilename = f"{safeBaseName}{extLower}"
	destPath = os.path.join(soundsDir, destFilename)

	# If a file with the same name already exists
	if os.path.exists(destPath):
		# If content is identical, reuse the existing file
		if os.path.getsize(destPath) == os.path.getsize(sourcePath):
			if _getFileHash(destPath) == sourceHash:
				return destFilename

		# Otherwise find a unique name (e.g. chime_1.wav)
		counter = 1
		while True:
			candidateName = f"{safeBaseName}_{counter}{extLower}"
			candidatePath = os.path.join(soundsDir, candidateName)
			if not os.path.exists(candidatePath):
				destFilename = candidateName
				destPath = candidatePath
				break
			if os.path.getsize(candidatePath) == os.path.getsize(sourcePath):
				if _getFileHash(candidatePath) == sourceHash:
					return candidateName
			counter += 1

	shutil.copy2(sourcePath, destPath)
	log.debug(f"Copied audio file from {sourcePath} to {destPath}")
	return destFilename


def resolveSoundPath(soundRef: Optional[str]) -> Optional[str]:
	"""Resolve a sound filename or path to an absolute path if the file exists.

	:param soundRef: Filename in the sounds directory or absolute path.
	:returns: Absolute path to the existing file, or None if not found.
	"""
	if not soundRef:
		return None

	# Check if soundRef is already an existing absolute path
	if os.path.isabs(soundRef) and os.path.isfile(soundRef):
		return os.path.abspath(soundRef)

	# Check inside add-on's sounds directory
	candidate = os.path.join(getSoundsDir(), soundRef)
	if os.path.isfile(candidate):
		return os.path.abspath(candidate)

	return None


def isSoundFileReferenced(filename: str, dictionaryFiles: list[str]) -> bool:
	"""Check if a sound filename is referenced in any of the given dictionary files."""
	soundTag = f"<sound:{filename}>"
	for dicPath in dictionaryFiles:
		if not os.path.isfile(dicPath):
			continue
		try:
			with open(dicPath, "r", encoding="utf_8_sig", errors="ignore") as f:
				content = f.read()
				if soundTag in content:
					return True
		except Exception:
			pass
	return False


def deleteSoundFileIfUnused(filename: str, dictionaryFiles: Optional[list[str]] = None) -> bool:
	"""Delete a sound file from the add-on's sounds directory if it is not referenced in dictionary files.

	:param filename: Base filename to check and potentially delete.
	:param dictionaryFiles: Optional list of .dic file paths. If None, checks are skipped and file is removed.
	:returns: True if deleted, False otherwise.
	"""
	soundsDir = getSoundsDir()
	targetPath = os.path.join(soundsDir, filename)
	if not os.path.isfile(targetPath):
		return False

	if dictionaryFiles and isSoundFileReferenced(filename, dictionaryFiles):
		return False

	try:
		os.remove(targetPath)
		log.debug(f"Removed unused sound file: {targetPath}")
		return True
	except OSError as e:
		log.warning(f"Could not remove sound file {targetPath}: {e}")
		return False
