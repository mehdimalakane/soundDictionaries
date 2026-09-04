# End-to-end integration test for Sound Dictionaries add-on
import unittest
import os
import tempfile
import shutil

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "soundDictionaries", "globalPlugins")))

from soundDictionaries import soundStorage
from soundDictionaries import soundPlayer
from soundDictionaries import dictionaryEntry
from soundDictionaries import speechExtension
from soundDictionaries import GlobalPlugin


class MockSpeechDict(list):
	fileName = None

	def __init__(self, fileName="test_dict.dic"):
		super().__init__()
		self.fileName = fileName

	def load(self, fileName=None):
		if fileName:
			self.fileName = fileName
		self.clear()
		if not os.path.isfile(self.fileName):
			return
		with open(self.fileName, "r", encoding="utf-8") as f:
			comment = ""
			for line in f:
				line = line.strip()
				if not line:
					continue
				if line.startswith("#"):
					comment = line[1:].strip()
				else:
					parts = line.split("\t")
					if len(parts) >= 2:
						entry = dictionaryEntry.SpeechDictEntry(parts[0], parts[1], comment) if dictionaryEntry.SpeechDictEntry else None
						if entry is None:
							# Fallback dummy entry
							class Dummy:
								def __init__(self, p, r, c):
									self.pattern = p
									self.replacement = r
									self.comment = c
									self.caseSensitive = True
									self.type = 0
									import re
									self.compiled = re.compile(re.escape(p))
								def sub(self, text):
									return dictionaryEntry.entrySub(self, text)
							entry = Dummy(parts[0], parts[1], comment)
						dictionaryEntry.prepareEntry(entry)
						self.append(entry)
						comment = ""

	def save(self, fileName=None):
		fn = fileName or self.fileName
		with open(fn, "w", encoding="utf-8") as f:
			for entry in self:
				if entry.comment:
					f.write(f"#{entry.comment}\n")
				f.write(f"{entry.pattern}\t{entry.replacement}\t1\t0\n")

	def sub(self, text):
		for entry in self:
			text = entry.sub(text)
		return text


class TestEndToEndIntegration(unittest.TestCase):

	def setUp(self):
		self.testDir = tempfile.mkdtemp(prefix="nvda_test_e2e_")
		self.origGetAddonDir = soundStorage.getAddonDir
		soundStorage.getAddonDir = lambda: self.testDir

		# Create a dummy external WAV and MP3 file
		self.externalWav = os.path.join(self.testDir, "user_laugh.wav")
		with open(self.externalWav, "wb") as f:
			f.write(b"RIFF laugh wav data")

		self.externalMp3 = os.path.join(self.testDir, "user_alert.mp3")
		with open(self.externalMp3, "wb") as f:
			f.write(b"ID3 alert mp3 data")

		# Track played sounds
		self.playedSounds = []
		self.origPlaySound = soundPlayer.playSound
		soundPlayer.playSound = lambda p: self.playedSounds.append(p) or True

	def tearDown(self):
		soundPlayer.playSound = self.origPlaySound
		soundStorage.getAddonDir = self.origGetAddonDir
		if os.path.isdir(self.testDir):
			shutil.rmtree(self.testDir, ignore_errors=True)

	def test_fullAddonLifecycle(self):
		# 1. Initialize plugin
		plugin = GlobalPlugin()
		self.assertIsNotNone(plugin)

		# 2. Simulate user adding an entry with WAV sound in a dictionary
		savedWavName = soundStorage.copySoundFile(self.externalWav)
		self.assertEqual(savedWavName, "user_laugh.wav")
		self.assertTrue(os.path.isfile(os.path.join(soundStorage.getSoundsDir(), savedWavName)))

		# 3. Simulate user adding an entry with MP3 sound (sound only, empty replacement)
		savedMp3Name = soundStorage.copySoundFile(self.externalMp3)
		self.assertEqual(savedMp3Name, "user_alert.mp3")
		self.assertTrue(os.path.isfile(os.path.join(soundStorage.getSoundsDir(), savedMp3Name)))

		# 4. Construct dictionary and save it to file
		dictFile = os.path.join(self.testDir, "default.dic")
		d = MockSpeechDict(dictFile)

		class DummyEntry:
			def __init__(self, p, r, comment):
				self.pattern = p
				self.replacement = r
				self.comment = comment
				self.caseSensitive = True
				self.type = 0
				import re
				self.compiled = re.compile(re.escape(p))
			def sub(self, text):
				return dictionaryEntry.entrySub(self, text)

		# Entry 1: lol -> laughing out loud + user_laugh.wav
		comment1 = dictionaryEntry.buildComment("laugh phrase", savedWavName)
		entry1 = DummyEntry("lol", "laughing out loud", comment1)
		dictionaryEntry.prepareEntry(entry1)
		d.append(entry1)

		# Entry 2: warning -> (empty replacement) + user_alert.mp3
		comment2 = dictionaryEntry.buildComment("", savedMp3Name)
		entry2 = DummyEntry("warning", "", comment2)
		dictionaryEntry.prepareEntry(entry2)
		d.append(entry2)

		# Save dictionary
		d.save()

		# Verify .dic contents: 100% compliant with standard 4-tab NVDA format
		with open(dictFile, "r", encoding="utf-8") as f:
			lines = f.readlines()
		self.assertEqual(len(lines), 4)
		self.assertTrue(lines[0].startswith("#laugh phrase <sound:user_laugh.wav>"))
		self.assertTrue(lines[1].startswith("lol\tlaughing out loud\t1\t0"))
		self.assertTrue(lines[2].startswith("#<sound:user_alert.mp3>"))
		self.assertTrue(lines[3].startswith("warning\t\t1\t0"))

		# 5. Reload dictionary from disk (simulating NVDA startup)
		reloadedDict = MockSpeechDict(dictFile)
		reloadedDict.load()
		self.assertEqual(len(reloadedDict), 2)
		self.assertEqual(reloadedDict[0].soundFileName, "user_laugh.wav")
		self.assertEqual(reloadedDict[0].userComment, "laugh phrase")
		self.assertEqual(reloadedDict[1].soundFileName, "user_alert.mp3")
		self.assertEqual(reloadedDict[1].userComment, "")

		# 6. Process text through dictionary (simulating NVDA speechDictHandler.processText)
		inputText = "There is a warning for you lol"
		played = []
		origPlay = soundPlayer.playSound
		soundPlayer.playSound = lambda fn: played.append(fn) or True
		try:
			processedText = reloadedDict.sub(inputText)
			expectedText = "There is a  for you laughing out loud"
			self.assertEqual(processedText, expectedText)
			self.assertEqual(played, ["user_laugh.wav", "user_alert.mp3"])
		finally:
			soundPlayer.playSound = origPlay

		# 7. Convert text to speech sequence with SoundCommands (backward compatibility check)
		legacySequence = [f"There is a {dictionaryEntry.makeSoundMarker('user_alert.mp3')} for you {dictionaryEntry.makeSoundMarker('user_laugh.wav')}laughing out loud"]
		speechSeq = speechExtension.splitSpeechSequenceWithSounds(legacySequence)
		# Should contain: ["There is a ", SoundCommand(user_alert.mp3), " for you ", SoundCommand(user_laugh.wav), "laughing out loud"]
		self.assertEqual(len(speechSeq), 5)
		self.assertEqual(speechSeq[0], "There is a ")
		self.assertIsInstance(speechSeq[1], speechExtension.SoundCommand)
		self.assertEqual(speechSeq[1].soundFileName, "user_alert.mp3")
		self.assertEqual(speechSeq[2], " for you ")
		self.assertIsInstance(speechSeq[3], speechExtension.SoundCommand)
		self.assertEqual(speechSeq[3].soundFileName, "user_laugh.wav")
		self.assertEqual(speechSeq[4], "laughing out loud")

		# 8. Dispatch sound commands as speech reaches them
		speechSeq[1].run()
		self.assertEqual(len(self.playedSounds), 1)
		self.assertTrue(self.playedSounds[0].endswith("user_alert.mp3"))

		speechSeq[3].run()
		self.assertEqual(len(self.playedSounds), 2)
		self.assertTrue(self.playedSounds[1].endswith("user_laugh.wav"))

		# 9. Clean up / terminate plugin
		plugin.terminate()


if __name__ == "__main__":
	unittest.main()
