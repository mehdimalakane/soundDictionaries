# Unit tests for dictionaryEntry module
import unittest
import os
import re

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "soundDictionaries", "globalPlugins")))

from soundDictionaries import dictionaryEntry, soundPlayer


class DummyEntry:
	def __init__(self, pattern, replacement, comment="", caseSensitive=True, entryType=0):
		self.pattern = pattern
		self.replacement = replacement
		self.comment = comment
		self.caseSensitive = caseSensitive
		self.type = entryType
		flags = re.UNICODE if caseSensitive else (re.UNICODE | re.IGNORECASE)
		if entryType == 1: # REGEXP
			self.compiled = re.compile(pattern, flags)
		elif entryType == 2: # WORD
			self.compiled = re.compile(rf"\b{re.escape(pattern)}\b", flags)
		else: # ANYWHERE
			self.compiled = re.compile(re.escape(pattern), flags)

	def sub(self, text):
		return dictionaryEntry.entrySub(self, text)


class TestDictionaryEntry(unittest.TestCase):

	def test_parseComment(self):
		# Simple comment with sound tag
		comment, sound = dictionaryEntry.parseComment("Fix pronunciation <sound:chime.wav>")
		self.assertEqual(comment, "Fix pronunciation")
		self.assertEqual(sound, "chime.wav")

		# Only sound tag, no user comment
		comment, sound = dictionaryEntry.parseComment("<sound:alert.mp3>")
		self.assertEqual(comment, "")
		self.assertEqual(sound, "alert.mp3")

		# Normal comment with no sound tag
		comment, sound = dictionaryEntry.parseComment("Normal comment")
		self.assertEqual(comment, "Normal comment")
		self.assertIsNone(sound)

		# Empty or None
		comment, sound = dictionaryEntry.parseComment("")
		self.assertEqual(comment, "")
		self.assertIsNone(sound)
		comment, sound = dictionaryEntry.parseComment(None)
		self.assertEqual(comment, "")
		self.assertIsNone(sound)

	def test_buildComment(self):
		# User comment with sound
		res = dictionaryEntry.buildComment("Fix pronunciation", "chime.wav")
		self.assertEqual(res, "Fix pronunciation <sound:chime.wav>")

		# No user comment, only sound
		res = dictionaryEntry.buildComment("", "alert.mp3")
		self.assertEqual(res, "<sound:alert.mp3>")

		# User comment, no sound
		res = dictionaryEntry.buildComment("My note", None)
		self.assertEqual(res, "My note")

		# Neither
		res = dictionaryEntry.buildComment("", None)
		self.assertEqual(res, "")

		# Overwriting an existing sound tag in user comment
		res = dictionaryEntry.buildComment("Note <sound:old.wav>", "new.mp3")
		self.assertEqual(res, "Note <sound:new.mp3>")

	def test_roundTripComment(self):
		origUser = "Custom phrase note"
		origSound = "laugh.wav"
		built = dictionaryEntry.buildComment(origUser, origSound)
		parsedUser, parsedSound = dictionaryEntry.parseComment(built)
		self.assertEqual(parsedUser, origUser)
		self.assertEqual(parsedSound, origSound)

	def test_encodeAndDecodeSoundFilename(self):
		filename = "douaa demo.wav"
		encoded = dictionaryEntry.encodeSoundFilename(filename)
		# Encoded string must only contain hex characters (no spaces, dots, colons)
		self.assertTrue(all(c in "0123456789abcdef" for c in encoded))
		self.assertNotIn(".", encoded)
		self.assertNotIn(" ", encoded)
		self.assertEqual(dictionaryEntry.decodeSoundFilename(encoded), filename)

	def test_makeSoundMarker(self):
		marker = dictionaryEntry.makeSoundMarker("ding.wav")
		self.assertTrue(marker.startswith("\ue000SND"))
		self.assertTrue(marker.endswith("\ue000"))
		self.assertNotIn(".", marker)

	def test_substitutionWithoutSound(self):
		entry = DummyEntry(pattern="brb", replacement="be right back", comment="standard entry")
		text = "I will brb soon"
		res = entry.sub(text)
		self.assertEqual(res, "I will be right back soon")

	def test_substitutionWithSoundAndEmptyReplacement(self):
		# Replaces the phrase entirely with sound (like JAWS)
		played = []
		origPlay = soundPlayer.playSound
		soundPlayer.playSound = lambda fn: played.append(fn) or True
		try:
			entry = DummyEntry(pattern="brb", replacement="", comment="<sound:doorbell.wav>")
			text = "I will brb soon"
			res = entry.sub(text)
			self.assertEqual(res, "I will  soon")
			self.assertEqual(played, ["doorbell.wav"])
		finally:
			soundPlayer.playSound = origPlay

	def test_substitutionWithSoundAndReplacement(self):
		# Plays sound AND speaks replacement
		played = []
		origPlay = soundPlayer.playSound
		soundPlayer.playSound = lambda fn: played.append(fn) or True
		try:
			entry = DummyEntry(pattern="lol", replacement="laughing out loud", comment="note <sound:laugh.mp3>")
			text = "That is funny lol haha"
			res = entry.sub(text)
			self.assertEqual(res, "That is funny laughing out loud haha")
			self.assertEqual(played, ["laugh.mp3"])
		finally:
			soundPlayer.playSound = origPlay

	def test_substitutionRegexWithCaptureGroup(self):
		# Regexp entry with capture group \1
		played = []
		origPlay = soundPlayer.playSound
		soundPlayer.playSound = lambda fn: played.append(fn) or True
		try:
			entry = DummyEntry(pattern=r"item(\d+)", replacement=r"number \1", comment="<sound:beep.wav>", entryType=1)
			text = "Check item42 here"
			res = entry.sub(text)
			self.assertEqual(res, "Check number 42 here")
			self.assertEqual(played, ["beep.wav"])
		finally:
			soundPlayer.playSound = origPlay

	def test_substitutionCaseSensitivity(self):
		played = []
		origPlay = soundPlayer.playSound
		soundPlayer.playSound = lambda fn: played.append(fn) or True
		try:
			# Case sensitive
			entryCS = DummyEntry(pattern="Cat", replacement="", comment="<sound:meow.wav>", caseSensitive=True)
			self.assertEqual(entryCS.sub("a Cat and a cat"), "a  and a cat")
			self.assertEqual(played, ["meow.wav"])

			played.clear()
			# Case insensitive
			entryCI = DummyEntry(pattern="Cat", replacement="", comment="<sound:meow.wav>", caseSensitive=False)
			self.assertEqual(entryCI.sub("a Cat and a cat"), "a  and a ")
			self.assertEqual(played, ["meow.wav"])
		finally:
			soundPlayer.playSound = origPlay

	def test_noMarkersInSubstitutedText(self):
		# Verify that no SND, \ue000, or marker tokens ever appear in substituted text
		played = []
		origPlay = soundPlayer.playSound
		soundPlayer.playSound = lambda fn: played.append(fn) or True
		try:
			entry = DummyEntry(pattern="Add context", replacement="", comment="<sound:preview.wav>")
			res = entry.sub("Please Add context here")
			self.assertNotIn("snd", res.lower())
			self.assertNotIn("\ue000", res)
			self.assertEqual(res, "Please  here")
			self.assertEqual(played, ["preview.wav"])
		finally:
			soundPlayer.playSound = origPlay


if __name__ == "__main__":
	unittest.main()
