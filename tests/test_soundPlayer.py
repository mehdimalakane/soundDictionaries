# Unit tests for soundPlayer module
import unittest
import os
import tempfile
import shutil

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "soundDictionaries", "globalPlugins")))

from soundDictionaries import soundStorage
from soundDictionaries import soundPlayer


class TestSoundPlayer(unittest.TestCase):

	def setUp(self):
		self.testDir = tempfile.mkdtemp(prefix="nvda_test_player_")
		self.origGetAddonDir = soundStorage.getAddonDir
		soundStorage.getAddonDir = lambda: self.testDir

		sDir = soundStorage.getSoundsDir()
		self.wavPath = os.path.join(sDir, "alert.wav")
		with open(self.wavPath, "wb") as f:
			f.write(b"RIFF dummy wav")

		self.mp3Path = os.path.join(sDir, "chime.mp3")
		with open(self.mp3Path, "wb") as f:
			f.write(b"ID3 dummy mp3")

	def tearDown(self):
		soundStorage.getAddonDir = self.origGetAddonDir
		if os.path.isdir(self.testDir):
			shutil.rmtree(self.testDir, ignore_errors=True)

	def test_playSoundNonExistent(self):
		# Should return False and not raise
		self.assertFalse(soundPlayer.playSound("non_existent.wav"))
		self.assertFalse(soundPlayer.playSound(""))
		self.assertFalse(soundPlayer.playSound(None))

	def test_routingWav(self):
		wavCalled = []
		origPlayWav = soundPlayer.playWav
		soundPlayer.playWav = lambda p: wavCalled.append(p) or True
		try:
			res = soundPlayer.playSound("alert.wav")
			self.assertTrue(res)
			self.assertEqual(len(wavCalled), 1)
			self.assertTrue(wavCalled[0].endswith("alert.wav"))
		finally:
			soundPlayer.playWav = origPlayWav

	def test_routingMp3(self):
		mp3Called = []
		origPlayMp3 = soundPlayer.playMp3
		soundPlayer.playMp3 = lambda p: mp3Called.append(p) or True
		try:
			res = soundPlayer.playSound("chime.mp3")
			self.assertTrue(res)
			self.assertEqual(len(mp3Called), 1)
			self.assertTrue(mp3Called[0].endswith("chime.mp3"))
		finally:
			soundPlayer.playMp3 = origPlayMp3

	def test_stopAudio(self):
		# stopAudio should not raise even if nothing is playing
		soundPlayer.stopAudio()

	def test_cancellationHooks(self):
		soundPlayer.registerCancellationHook()
		soundPlayer.unregisterCancellationHook()


if __name__ == "__main__":
	unittest.main()
