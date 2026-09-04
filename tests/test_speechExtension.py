# Unit tests for speechExtension module
import unittest
import os
import tempfile
import shutil

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "soundDictionaries", "globalPlugins")))

from soundDictionaries import soundStorage
from soundDictionaries import soundPlayer
from soundDictionaries import speechExtension
from soundDictionaries.speechExtension import SoundCommand, splitSpeechSequenceWithSounds


class TestSpeechExtension(unittest.TestCase):

	def setUp(self):
		self.testDir = tempfile.mkdtemp(prefix="nvda_test_speech_")
		self.origGetAddonDir = soundStorage.getAddonDir
		soundStorage.getAddonDir = lambda: self.testDir

		# Create test sound files
		sDir = soundStorage.getSoundsDir()
		with open(os.path.join(sDir, "bell.wav"), "wb") as f:
			f.write(b"RIFF bell")
		with open(os.path.join(sDir, "chime.mp3"), "wb") as f:
			f.write(b"ID3 chime")

	def tearDown(self):
		soundStorage.getAddonDir = self.origGetAddonDir
		if os.path.isdir(self.testDir):
			shutil.rmtree(self.testDir, ignore_errors=True)

	def test_pureTextSequence(self):
		seq = ["Hello world", "how are you today?"]
		res = splitSpeechSequenceWithSounds(seq)
		self.assertEqual(res, seq)

	def test_singleSoundOnly(self):
		# Replaced completely by sound (legacy marker)
		seq = ["\ue000SOUND:bell.wav\ue000"]
		res = splitSpeechSequenceWithSounds(seq)
		self.assertEqual(len(res), 1)
		self.assertIsInstance(res[0], SoundCommand)
		self.assertEqual(res[0].soundFileName, "bell.wav")
		self.assertTrue(os.path.isfile(res[0].soundPath))

	def test_singleSoundOnlyHex(self):
		# Hex marker (symbol-safe)
		from soundDictionaries.dictionaryEntry import makeSoundMarker
		seq = [makeSoundMarker("bell.wav")]
		res = splitSpeechSequenceWithSounds(seq)
		self.assertEqual(len(res), 1)
		self.assertIsInstance(res[0], SoundCommand)
		self.assertEqual(res[0].soundFileName, "bell.wav")
		self.assertTrue(os.path.isfile(res[0].soundPath))

	def test_soundInSentence(self):
		from soundDictionaries.dictionaryEntry import makeSoundMarker
		seq = [f"I will be {makeSoundMarker('bell.wav')} back soon"]
		res = splitSpeechSequenceWithSounds(seq)
		self.assertEqual(len(res), 3)
		self.assertEqual(res[0], "I will be ")
		self.assertIsInstance(res[1], SoundCommand)
		self.assertEqual(res[1].soundFileName, "bell.wav")
		self.assertEqual(res[2], " back soon")

	def test_multipleSoundsInSentence(self):
		from soundDictionaries.dictionaryEntry import makeSoundMarker
		seq = [f"Start {makeSoundMarker('bell.wav')} middle {makeSoundMarker('chime.mp3')} end"]
		res = splitSpeechSequenceWithSounds(seq)
		self.assertEqual(len(res), 5)
		self.assertEqual(res[0], "Start ")
		self.assertIsInstance(res[1], SoundCommand)
		self.assertEqual(res[1].soundFileName, "bell.wav")
		self.assertEqual(res[2], " middle ")
		self.assertIsInstance(res[3], SoundCommand)
		self.assertEqual(res[3].soundFileName, "chime.mp3")
		self.assertEqual(res[4], " end")

	def test_adjacentSounds(self):
		from soundDictionaries.dictionaryEntry import makeSoundMarker
		seq = [f"{makeSoundMarker('bell.wav')}{makeSoundMarker('chime.mp3')}"]
		res = splitSpeechSequenceWithSounds(seq)
		self.assertEqual(len(res), 2)
		self.assertIsInstance(res[0], SoundCommand)
		self.assertEqual(res[0].soundFileName, "bell.wav")
		self.assertIsInstance(res[1], SoundCommand)
		self.assertEqual(res[1].soundFileName, "chime.mp3")

	def test_strippedDotFallback(self):
		# If symbol processor stripped dot in legacy marker, fallback should find bell.wav
		seq = ["\ue000SOUND:bell wav\ue000"]
		res = splitSpeechSequenceWithSounds(seq)
		self.assertEqual(len(res), 1)
		self.assertIsInstance(res[0], SoundCommand)
		self.assertEqual(res[0].soundFileName, "bell.wav")
		self.assertTrue(os.path.isfile(res[0].soundPath))

	def test_nonStringObjectsPreserved(self):
		dummyCommand = object()
		seq = ["Text before ", dummyCommand, " \ue000SOUND:bell.wav\ue000 text after"]
		res = splitSpeechSequenceWithSounds(seq)
		self.assertEqual(len(res), 5)
		self.assertEqual(res[0], "Text before ")
		self.assertIs(res[1], dummyCommand)
		self.assertEqual(res[2], " ")
		self.assertIsInstance(res[3], SoundCommand)
		self.assertEqual(res[4], " text after")

	def test_soundCommandRun(self):
		played = []
		origPlaySound = soundPlayer.playSound
		soundPlayer.playSound = lambda path: played.append(path)
		try:
			cmd = SoundCommand("bell.wav", "C:/path/bell.wav")
			cmd.run()
			self.assertEqual(played, ["C:/path/bell.wav"])
		finally:
			soundPlayer.playSound = origPlaySound


if __name__ == "__main__":
	unittest.main()
