# Unit tests for soundStorage module
import unittest
import os
import tempfile
import shutil

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "soundDictionaries", "globalPlugins")))

from soundDictionaries import soundStorage


class TestSoundStorage(unittest.TestCase):

	def setUp(self):
		self.testDir = tempfile.mkdtemp(prefix="nvda_test_storage_")
		self.origGetAddonDir = soundStorage.getAddonDir
		soundStorage.getAddonDir = lambda: self.testDir

	def tearDown(self):
		soundStorage.getAddonDir = self.origGetAddonDir
		if os.path.isdir(self.testDir):
			shutil.rmtree(self.testDir, ignore_errors=True)

	def test_getSoundsDir(self):
		sDir = soundStorage.getSoundsDir()
		self.assertTrue(os.path.isdir(sDir))
		self.assertEqual(sDir, os.path.join(self.testDir, "sounds"))

	def test_copyWavAndMp3(self):
		# Create dummy wav
		srcWav = os.path.join(self.testDir, "sample.wav")
		with open(srcWav, "wb") as f:
			f.write(b"RIFF dummy wav data 12345")

		# Create dummy mp3
		srcMp3 = os.path.join(self.testDir, "sample.mp3")
		with open(srcMp3, "wb") as f:
			f.write(b"ID3 dummy mp3 data 67890")

		destWav = soundStorage.copySoundFile(srcWav)
		self.assertEqual(destWav, "sample.wav")
		self.assertTrue(os.path.isfile(os.path.join(soundStorage.getSoundsDir(), "sample.wav")))

		destMp3 = soundStorage.copySoundFile(srcMp3)
		self.assertEqual(destMp3, "sample.mp3")
		self.assertTrue(os.path.isfile(os.path.join(soundStorage.getSoundsDir(), "sample.mp3")))

	def test_unsupportedFormatRejection(self):
		srcTxt = os.path.join(self.testDir, "sample.txt")
		with open(srcTxt, "w") as f:
			f.write("test")

		with self.assertRaises(ValueError):
			soundStorage.copySoundFile(srcTxt)

	def test_deduplicationSameContent(self):
		srcWav = os.path.join(self.testDir, "test.wav")
		with open(srcWav, "wb") as f:
			f.write(b"RIFF identical content")

		name1 = soundStorage.copySoundFile(srcWav)
		name2 = soundStorage.copySoundFile(srcWav)
		self.assertEqual(name1, name2)
		self.assertEqual(name1, "test.wav")

	def test_collisionDifferentContent(self):
		src1 = os.path.join(self.testDir, "source1.wav")
		with open(src1, "wb") as f:
			f.write(b"RIFF content A")

		# Create a different file with same name elsewhere
		subDir = os.path.join(self.testDir, "sub")
		os.makedirs(subDir)
		src2 = os.path.join(subDir, "source1.wav")
		with open(src2, "wb") as f:
			f.write(b"RIFF content B (different)")

		name1 = soundStorage.copySoundFile(src1)
		name2 = soundStorage.copySoundFile(src2)
		self.assertEqual(name1, "source1.wav")
		self.assertEqual(name2, "source1_1.wav")
		self.assertTrue(os.path.isfile(os.path.join(soundStorage.getSoundsDir(), "source1.wav")))
		self.assertTrue(os.path.isfile(os.path.join(soundStorage.getSoundsDir(), "source1_1.wav")))

	def test_resolveSoundPath(self):
		srcWav = os.path.join(self.testDir, "chime.wav")
		with open(srcWav, "wb") as f:
			f.write(b"RIFF chime")
		savedName = soundStorage.copySoundFile(srcWav)

		resolved = soundStorage.resolveSoundPath(savedName)
		self.assertIsNotNone(resolved)
		self.assertTrue(os.path.isfile(resolved))

		# Absolute path
		resolvedAbs = soundStorage.resolveSoundPath(resolved)
		self.assertEqual(resolved, resolvedAbs)

		# Non-existent
		self.assertIsNone(soundStorage.resolveSoundPath("non_existent.wav"))
		self.assertIsNone(soundStorage.resolveSoundPath(""))
		self.assertIsNone(soundStorage.resolveSoundPath(None))

	def test_isSoundFileReferencedAndDelete(self):
		sDir = soundStorage.getSoundsDir()
		soundPath = os.path.join(sDir, "bell.wav")
		with open(soundPath, "wb") as f:
			f.write(b"RIFF bell")

		dicPath = os.path.join(self.testDir, "default.dic")
		with open(dicPath, "w", encoding="utf-8") as f:
			f.write("# comment <sound:bell.wav>\npattern\treplacement\t0\t0\n")

		self.assertTrue(soundStorage.isSoundFileReferenced("bell.wav", [dicPath]))
		self.assertFalse(soundStorage.isSoundFileReferenced("other.wav", [dicPath]))

		# Should not delete if referenced
		deleted = soundStorage.deleteSoundFileIfUnused("bell.wav", [dicPath])
		self.assertFalse(deleted)
		self.assertTrue(os.path.isfile(soundPath))

		# Should delete if not referenced
		deleted = soundStorage.deleteSoundFileIfUnused("bell.wav", [])
		self.assertTrue(deleted)
		self.assertFalse(os.path.isfile(soundPath))


if __name__ == "__main__":
	unittest.main()
