# A part of Sound Dictionaries add-on for NVDA
# Copyright (C) 2026
# Licensed under GNU General Public License version 2 or later.

try:
	import globalPluginHandler
	_BasePlugin = globalPluginHandler.GlobalPlugin
except ImportError:
	_BasePlugin = object

try:
	from logHandler import log
except ImportError:
	import logging
	log = logging.getLogger("soundDictionaries")

from . import soundStorage
from . import soundPlayer
from . import speechExtension
from . import guiExtension


class GlobalPlugin(_BasePlugin):
	"""Global plugin for Sound Dictionaries.
	Integrates custom WAV and MP3 audio file assignment into NVDA speech dictionaries.
	"""

	def __init__(self):
		super().__init__()
		log.info("Sound Dictionaries: Initializing add-on...")
		try:
			# Ensure sounds storage directory exists in the add-on folder
			soundStorage.getSoundsDir()

			# Initialize speech system hooks (sequence splitting, SoundCommand, cancellation)
			speechExtension.initializeSpeechHooks()

			# Initialize GUI hooks (enhanced dictionary dialogs with sound controls)
			guiExtension.patchGui()

			log.info("Sound Dictionaries: Initialized successfully.")
		except Exception as e:
			log.exception(f"Sound Dictionaries: Failed to initialize: {e}")

	def terminate(self):
		"""Clean up and restore all NVDA systems when add-on is unloaded or NVDA shuts down."""
		log.info("Sound Dictionaries: Terminating add-on...")
		try:
			guiExtension.unpatchGui()
		except Exception as e:
			log.debugWarning(f"Sound Dictionaries: Error unpatching GUI: {e}")

		try:
			speechExtension.terminateSpeechHooks()
		except Exception as e:
			log.debugWarning(f"Sound Dictionaries: Error terminating speech hooks: {e}")

		try:
			soundPlayer.stopAudio()
		except Exception as e:
			log.debugWarning(f"Sound Dictionaries: Error stopping audio: {e}")

		if hasattr(super(), "terminate"):
			super().terminate()
		log.info("Sound Dictionaries: Terminated cleanly.")
