# Unit tests for guiExtension module
import unittest
import os
import tempfile
import shutil
try:
	import wx
except ImportError:
	wx = None

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "soundDictionaries", "globalPlugins")))

from soundDictionaries import soundStorage
from soundDictionaries import soundPlayer
from soundDictionaries import guiExtension
from soundDictionaries.guiExtension import (
	EnhancedDictionaryEntryDialog,
	EnhancedDictionaryDialog,
)


if wx is not None:
	class MockGuiHelper:
		class BoxSizerHelper:
			def __init__(self, parent, orientation=wx.VERTICAL, sizer=None):
				self.parent = parent
				self.sizer = sizer or wx.BoxSizer(orientation)

			def addLabeledControl(self, labelText, controlClass, style=0, choices=None):
				lbl = wx.StaticText(self.parent, label=labelText)
				self.sizer.Add(lbl)
				if choices is not None:
					ctrl = controlClass(self.parent, choices=choices, style=style)
				elif style:
					ctrl = controlClass(self.parent, style=style)
				else:
					ctrl = controlClass(self.parent)
				self.sizer.Add(ctrl)
				return ctrl

			def addItem(self, item, flag=0):
				if isinstance(item, MockGuiHelper.ButtonHelper):
					self.sizer.Add(item.sizer, flag=flag)
				else:
					self.sizer.Add(item, flag=flag)
				return item

			def addDialogDismissButtons(self, flags, separated=True):
				btnSizer = wx.StdDialogButtonSizer()
				if flags & wx.OK:
					btnSizer.AddButton(wx.Button(self.parent, wx.ID_OK))
				if flags & wx.CANCEL:
					btnSizer.AddButton(wx.Button(self.parent, wx.ID_CANCEL))
				btnSizer.Realize()
				self.sizer.Add(btnSizer)

		class ButtonHelper:
			def __init__(self, orientation=wx.HORIZONTAL):
				self.sizer = wx.BoxSizer(orientation)

			def addButton(self, parent, label):
				btn = wx.Button(parent, label=label)
				self.sizer.Add(btn)
				return btn
else:
	MockGuiHelper = None


@unittest.skipIf(wx is None, "wxPython is not installed in the test environment")
class TestGuiExtension(unittest.TestCase):

	@classmethod
	def setUpClass(cls):
		cls.app = wx.App()

	@classmethod
	def tearDownClass(cls):
		cls.app.Destroy()

	def setUp(self):
		self.testDir = tempfile.mkdtemp(prefix="nvda_test_gui_")
		self.origGetAddonDir = soundStorage.getAddonDir
		soundStorage.getAddonDir = lambda: self.testDir

		# Inject mock guiHelper if needed
		self.origGuiHelper = guiExtension.guiHelper
		guiExtension.guiHelper = MockGuiHelper

	def tearDown(self):
		guiExtension.guiHelper = self.origGuiHelper
		soundStorage.getAddonDir = self.origGetAddonDir
		if os.path.isdir(self.testDir):
			shutil.rmtree(self.testDir, ignore_errors=True)

	def test_entryDialogSoundControls(self):
		frame = wx.Frame(None)
		try:
			dlg = EnhancedDictionaryEntryDialog(frame, title="Test Entry Dialog")

			# Verify sound controls exist
			self.assertIsNotNone(dlg.soundFileTextCtrl)
			self.assertIsNotNone(dlg.browseSoundBtn)
			self.assertIsNotNone(dlg.playSoundBtn)
			self.assertIsNotNone(dlg.clearSoundBtn)

			# Initially no sound assigned
			self.assertEqual(dlg.soundFileTextCtrl.GetValue(), "")
			self.assertFalse(dlg.playSoundBtn.IsEnabled())
			self.assertFalse(dlg.clearSoundBtn.IsEnabled())

			# Assign sound
			dlg.setSoundFileName("bell.wav")
			self.assertEqual(dlg.soundFileTextCtrl.GetValue(), "bell.wav")
			self.assertEqual(dlg.getSoundFileName(), "bell.wav")
			self.assertTrue(dlg.playSoundBtn.IsEnabled())
			self.assertTrue(dlg.clearSoundBtn.IsEnabled())

			# Clear sound
			dlg.onClearSound(None)
			self.assertEqual(dlg.soundFileTextCtrl.GetValue(), "")
			self.assertIsNone(dlg.getSoundFileName())
			self.assertFalse(dlg.playSoundBtn.IsEnabled())
			self.assertFalse(dlg.clearSoundBtn.IsEnabled())

			dlg.Destroy()
		finally:
			frame.Destroy()

	def test_entryDialogSetAndGetType(self):
		frame = wx.Frame(None)
		try:
			dlg = EnhancedDictionaryEntryDialog(frame)
			dlg.setType(0)
			self.assertEqual(dlg.typeRadioBox.GetSelection(), 0)
			dlg.setType(2)
			self.assertEqual(dlg.typeRadioBox.GetSelection(), 2)
			dlg.Destroy()
		finally:
			frame.Destroy()

	def test_dictionaryDialogSoundColumn(self):
		frame = wx.Frame(None)
		try:
			# Mock a SpeechDict
			class MockSpeechDict(list):
				fileName = "test.dic"
				def save(self): pass

			speechDict = MockSpeechDict()
			dlg = EnhancedDictionaryDialog(frame, title="Test Dialog", speechDict=speechDict)

			mainSizer = wx.BoxSizer(wx.VERTICAL)
			dlg.makeSettings(mainSizer)

			# Check columns count
			self.assertEqual(dlg.dictList.GetColumnCount(), 6)
			# Column headers: Comment (0), Pattern (1), Replacement (2), Sound (3), case (4), Type (5)
			colSound = dlg.dictList.GetColumn(3)
			self.assertEqual(colSound.GetText(), "Sound")

			dlg.Destroy()
		finally:
			frame.Destroy()


	def test_soundFileTextCtrlIsTabAccessible(self):
		frame = wx.Frame(None)
		try:
			dlg = EnhancedDictionaryEntryDialog(frame)
			# Must accept focus from keyboard (Tab key)
			self.assertTrue(dlg.soundFileTextCtrl.AcceptsFocusFromKeyboard())
			self.assertTrue(dlg.soundFileTextCtrl.IsEditable())
			dlg.Destroy()
		finally:
			frame.Destroy()

	def test_onSoundFileTextChange(self):
		frame = wx.Frame(None)
		try:
			dlg = EnhancedDictionaryEntryDialog(frame)
			self.assertFalse(dlg.playSoundBtn.IsEnabled())
			self.assertFalse(dlg.clearSoundBtn.IsEnabled())

			# User types/pastes a sound filename
			dlg.soundFileTextCtrl.SetValue("chime.mp3")
			self.assertTrue(dlg.playSoundBtn.IsEnabled())
			self.assertTrue(dlg.clearSoundBtn.IsEnabled())
			self.assertEqual(dlg.getSoundFileName(), "chime.mp3")

			# User deletes text
			dlg.soundFileTextCtrl.SetValue("")
			self.assertFalse(dlg.playSoundBtn.IsEnabled())
			self.assertFalse(dlg.clearSoundBtn.IsEnabled())
			self.assertIsNone(dlg.getSoundFileName())
			dlg.Destroy()
		finally:
			frame.Destroy()

	def test_onBrowseSoundNoUnboundLocalError(self):
		frame = wx.Frame(None)
		try:
			dlg = EnhancedDictionaryEntryDialog(frame)
			# Mock wx.FileDialog so it doesn't block the test
			origFileDialog = wx.FileDialog
			class MockFileDialog:
				def __init__(self, parent, message="", wildcard="", defaultDir="", style=0):
					self.parent = parent
					self.message = message
					self.wildcard = wildcard
					self.defaultDir = defaultDir
				def ShowModal(self):
					return wx.ID_CANCEL
				def Destroy(self):
					pass
			wx.FileDialog = MockFileDialog
			try:
				# This previously crashed with UnboundLocalError: cannot access local variable '_'
				dlg.onBrowseSound(None)
			finally:
				wx.FileDialog = origFileDialog
			dlg.Destroy()
		finally:
			frame.Destroy()

	def test_browseAndPreviewSoundPreservesPath(self):
		frame = wx.Frame(None)
		try:
			dlg = EnhancedDictionaryEntryDialog(frame)
			testWav = os.path.join(self.testDir, "user_preview.wav")
			with open(testWav, "wb") as f:
				f.write(b"RIFF dummy test")

			origFileDialog = wx.FileDialog
			class MockFileDialog:
				def __init__(self, parent, message="", wildcard="", defaultDir="", style=0):
					pass
				def ShowModal(self):
					return wx.ID_OK
				def GetPath(self):
					return testWav
				def Destroy(self):
					pass

			wx.FileDialog = MockFileDialog
			try:
				dlg.onBrowseSound(None)
				# Verify pending path is preserved
				self.assertEqual(dlg._pendingSoundSourcePath, testWav)
				self.assertEqual(dlg._selectedSoundFileName, "user_preview.wav")
				self.assertEqual(dlg.soundFileTextCtrl.GetValue(), "user_preview.wav")

				# Verify preview plays the pending path
				played = []
				origPlaySound = soundPlayer.playSound
				soundPlayer.playSound = lambda p: played.append(p) or True
				try:
					dlg.onPlaySound(None)
					self.assertEqual(played, [testWav])
				finally:
					soundPlayer.playSound = origPlaySound

				# Verify onOk copies the file into soundsDir
				dlg.patternTextCtrl.SetValue("myphrase")
				mockEvt = wx.CommandEvent(wx.wxEVT_BUTTON, wx.ID_OK)
				dlg.onOk(mockEvt)

				# File should now be in soundsDir
				copiedPath = os.path.join(soundStorage.getSoundsDir(), "user_preview.wav")
				self.assertTrue(os.path.isfile(copiedPath))
			finally:
				wx.FileDialog = origFileDialog
			dlg.Destroy()
		finally:
			frame.Destroy()


	def test_onOkWithRealSpeechDictEntry(self):
		frame = wx.Frame(None)
		try:
			class MockSpeechDictEntry:
				def __init__(self, pattern, replacement, comment="", caseSensitive=True, type=0):
					self.pattern = pattern
					self.replacement = replacement
					self.comment = comment
					self.caseSensitive = caseSensitive
					self.type = type

				def sub(self, text):
					return text

			origSDE = guiExtension.SpeechDictEntry
			guiExtension.SpeechDictEntry = MockSpeechDictEntry
			try:
				dlg = EnhancedDictionaryEntryDialog(frame)
				dlg.patternTextCtrl.SetValue("hello")
				dlg.replacementTextCtrl.SetValue("world")
				dlg.setSoundFileName("bell.wav")
				mockEvt = wx.CommandEvent(wx.wxEVT_BUTTON, wx.ID_OK)
				dlg.onOk(mockEvt)
				self.assertIsNotNone(dlg.dictEntry)
				self.assertEqual(dlg.dictEntry.soundFileName, "bell.wav")
				self.assertEqual(dlg.dictEntry.comment, "<sound:bell.wav>")
				dlg.Destroy()
			finally:
				guiExtension.SpeechDictEntry = origSDE
		finally:
			frame.Destroy()


if __name__ == "__main__":
	unittest.main()


