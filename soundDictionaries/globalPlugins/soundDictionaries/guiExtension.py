# A part of Sound Dictionaries add-on for NVDA
# Copyright (C) 2026
# Licensed under GNU General Public License version 2 or later.

import os
from re import error as RegexpError
from typing import Optional

try:
	_
except NameError:
	def _(s: str) -> str:
		return s

try:
	import wx
except ImportError:
	wx = None

try:
	import gui
	import gui.contextHelp
	from gui import guiHelper
	from gui.settingsDialogs import SettingsDialog
except ImportError:
	gui = None
	guiHelper = None
	SettingsDialog = object

try:
	import globalVars
	import speechDictHandler
	from speechDictHandler.types import DictionaryType, EntryType, SpeechDict, SpeechDictEntry
except ImportError:
	globalVars = None
	speechDictHandler = None
	DictionaryType = None
	EntryType = None
	SpeechDict = None
	SpeechDictEntry = None

try:
	from logHandler import log
except ImportError:
	import logging
	log = logging.getLogger("soundDictionaries")

from . import soundPlayer
from . import soundStorage
from . import dictionaryEntry
from .dictionaryEntry import buildComment, prepareEntry, suppressSound

# Original classes saved for clean restoration on plugin terminate
_originalDictionaryEntryDialog = None
_originalDictionaryDialog = None
_originalDefaultDictionaryDialog = None
_originalVoiceDictionaryDialog = None
_originalTemporaryDictionaryDialog = None
_originalGuiDefaultDialog = None
_originalGuiVoiceDialog = None
_originalGuiTemporaryDialog = None


_entryDialogBases = []
if gui and hasattr(gui, "contextHelp") and hasattr(gui.contextHelp, "ContextHelpMixin"):
	_entryDialogBases.append(gui.contextHelp.ContextHelpMixin)
if wx and hasattr(wx, "Dialog"):
	_entryDialogBases.append(wx.Dialog)
if not _entryDialogBases:
	_entryDialogBases.append(object)


class EnhancedDictionaryEntryDialog(*_entryDialogBases):
	"""Enhanced Dictionary Entry dialog with audio file selection, playback, and removal."""

	helpId = "SpeechDictionaries"

	def __init__(self, parent, title=_("Edit Dictionary Entry")):
		if wx and hasattr(wx, "Dialog") and isinstance(self, wx.Dialog):
			wx.Dialog.__init__(self, parent, title=title)
		else:
			super().__init__()
		self._selectedSoundFileName: Optional[str] = None
		self._pendingSoundSourcePath: Optional[str] = None

		mainSizer = wx.BoxSizer(wx.VERTICAL)
		sHelper = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)

		# Pattern
		patternLabelText = _("&Pattern")
		self.patternTextCtrl = sHelper.addLabeledControl(patternLabelText, wx.TextCtrl)

		# Replacement
		replacementLabelText = _("&Replacement")
		self.replacementTextCtrl = sHelper.addLabeledControl(replacementLabelText, wx.TextCtrl)

		# Comment
		commentLabelText = _("&Comment")
		self.commentTextCtrl = sHelper.addLabeledControl(commentLabelText, wx.TextCtrl)

		# --- Audio File Controls ---
		# Translators: Label for the assigned audio file field in the dictionary entry dialog.
		soundLabelText = _("&Audio file:")
		self.soundFileTextCtrl = sHelper.addLabeledControl(
			soundLabelText,
			wx.TextCtrl,
		)
		self.soundFileTextCtrl.Bind(wx.EVT_TEXT, self.onSoundFileTextChange)

		soundButtons = guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		# Translators: Button to browse for an audio file.
		self.browseSoundBtn = soundButtons.addButton(self, label=_("&Browse..."))
		self.browseSoundBtn.Bind(wx.EVT_BUTTON, self.onBrowseSound)

		# Translators: Button to play the assigned audio file.
		self.playSoundBtn = soundButtons.addButton(self, label=_("Pla&y sound"))
		self.playSoundBtn.Bind(wx.EVT_BUTTON, self.onPlaySound)
		self.playSoundBtn.Enable(False)

		# Translators: Button to clear the assigned audio file.
		self.clearSoundBtn = soundButtons.addButton(self, label=_("Clear soun&d"))
		self.clearSoundBtn.Bind(wx.EVT_BUTTON, self.onClearSound)
		self.clearSoundBtn.Enable(False)

		sHelper.addItem(soundButtons)

		# Case sensitive
		caseSensitiveText = _("Case &sensitive")
		self.caseSensitiveCheckBox = sHelper.addItem(wx.CheckBox(self, label=caseSensitiveText))

		# Type radio box
		typeText = _("&Type")
		if _originalDictionaryEntryDialog and hasattr(_originalDictionaryEntryDialog, "TYPE_LABELS"):
			typeChoices = [
				_originalDictionaryEntryDialog.TYPE_LABELS[i]
				for i in _originalDictionaryEntryDialog.TYPE_LABELS_ORDERING
			]
		elif EntryType and hasattr(EntryType, "ANYWHERE"):
			typeChoices = list(EntryType.ANYWHERE._displayStringLabels.values())
		else:
			typeChoices = [
				_("&Anywhere"),
				_("Whole &word"),
				_("&Part of word"),
				_("&Start of word"),
				_("E&nd of word"),
				_("Regular &expression"),
				_("&Unix shell-style wildcards"),
			]

		self.typeRadioBox = sHelper.addItem(
			wx.RadioBox(self, label=typeText, choices=typeChoices, style=wx.RA_SPECIFY_ROWS),
		)

		sHelper.addDialogDismissButtons(wx.OK | wx.CANCEL, separated=True)

		border = getattr(guiHelper, "BORDER_FOR_DIALOGS", 10) if guiHelper else 10
		mainSizer.Add(sHelper.sizer, border=border, flag=wx.ALL)
		mainSizer.Fit(self)
		self.SetSizer(mainSizer)
		self.CentreOnParent()
		if EntryType:
			self.setType(EntryType.ANYWHERE)
		self.patternTextCtrl.SetFocus()

		self.Bind(wx.EVT_BUTTON, self.onOk, id=wx.ID_OK)
		self.Bind(wx.EVT_BUTTON, self.onCancel, id=wx.ID_CANCEL)
		self.Bind(wx.EVT_CLOSE, self.onClose)

	def getType(self):
		typeRadioValue = self.typeRadioBox.GetSelection()
		if typeRadioValue == wx.NOT_FOUND:
			return EntryType.ANYWHERE if EntryType else 0
		if _originalDictionaryEntryDialog and hasattr(_originalDictionaryEntryDialog, "TYPE_LABELS_ORDERING"):
			return _originalDictionaryEntryDialog.TYPE_LABELS_ORDERING[typeRadioValue]
		return typeRadioValue

	def setType(self, entryType) -> None:
		if _originalDictionaryEntryDialog and hasattr(_originalDictionaryEntryDialog, "TYPE_LABELS_ORDERING"):
			idx = _originalDictionaryEntryDialog.TYPE_LABELS_ORDERING.index(entryType)
			self.typeRadioBox.SetSelection(idx)
		elif isinstance(entryType, int):
			self.typeRadioBox.SetSelection(entryType)

	def onSoundFileTextChange(self, evt: wx.CommandEvent) -> None:
		"""Update button states and internal sound references when text is typed or changed."""
		val = self.soundFileTextCtrl.GetValue().strip()
		hasSound = bool(val)
		self.playSoundBtn.Enable(hasSound)
		self.clearSoundBtn.Enable(hasSound)
		if not val:
			self._selectedSoundFileName = None
			self._pendingSoundSourcePath = None
		elif os.path.isabs(val) and os.path.isfile(val):
			self._pendingSoundSourcePath = val
			self._selectedSoundFileName = os.path.basename(val)
		else:
			# If the text in the control matches the basename of the currently pending file, keep the pending path!
			if self._pendingSoundSourcePath and os.path.basename(self._pendingSoundSourcePath) == val:
				self._selectedSoundFileName = val
			else:
				self._selectedSoundFileName = val
		evt.Skip()

	def setSoundFileName(self, filename: Optional[str]) -> None:
		"""Set the current sound filename for an existing entry."""
		self._selectedSoundFileName = filename
		self._pendingSoundSourcePath = None
		self.soundFileTextCtrl.ChangeValue(filename or "")
		hasSound = bool(filename)
		self.playSoundBtn.Enable(hasSound)
		self.clearSoundBtn.Enable(hasSound)

	def getSoundFileName(self) -> Optional[str]:
		return self._selectedSoundFileName

	def onBrowseSound(self, evt: wx.CommandEvent) -> None:
		"""Open file dialog to choose a WAV or MP3 audio file."""
		wildcard = (
			"Audio files (*.wav;*.mp3)|*.wav;*.mp3|"
			"WAV files (*.wav)|*.wav|"
			"MP3 files (*.mp3)|*.mp3|"
			"All files (*.*)|*.*"
		)
		defaultDir = os.path.expanduser("~")
		currentVal = self.soundFileTextCtrl.GetValue().strip()
		if currentVal and os.path.isabs(currentVal) and os.path.isdir(os.path.dirname(currentVal)):
			defaultDir = os.path.dirname(currentVal)

		dlg = wx.FileDialog(
			self,
			message=_("Select Audio File for Phrase"),
			wildcard=wildcard,
			defaultDir=defaultDir,
			style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
		)
		try:
			if hasattr(gui, "message") and hasattr(gui.message, "displayDialogAsModal"):
				res = gui.message.displayDialogAsModal(dlg)
			else:
				res = dlg.ShowModal()

			if res == wx.ID_OK:
				chosenPath = dlg.GetPath()
				rootPath, ext = os.path.splitext(chosenPath)
				if ext.lower() not in soundStorage.SUPPORTED_EXTENSIONS:
					if gui and hasattr(gui, "messageBox"):
						gui.messageBox(
							_("Only WAV and MP3 audio files are supported."),
							_("Invalid File Format"),
							wx.OK | wx.ICON_WARNING,
							self,
						)
					return

				self._pendingSoundSourcePath = chosenPath
				self._selectedSoundFileName = os.path.basename(chosenPath)
				self.soundFileTextCtrl.ChangeValue(self._selectedSoundFileName)
				self.playSoundBtn.Enable(True)
				self.clearSoundBtn.Enable(True)
				self.soundFileTextCtrl.SetFocus()
		finally:
			dlg.Destroy()

	def onPlaySound(self, evt: wx.CommandEvent) -> None:
		"""Preview the selected audio file."""
		if self._pendingSoundSourcePath and os.path.isfile(self._pendingSoundSourcePath):
			soundPlayer.playSound(self._pendingSoundSourcePath)
		elif self._selectedSoundFileName:
			soundPlayer.playSound(self._selectedSoundFileName)
		else:
			val = self.soundFileTextCtrl.GetValue().strip()
			if val:
				soundPlayer.playSound(val)

	def onClearSound(self, evt: wx.CommandEvent) -> None:
		"""Clear the assigned audio file."""
		soundPlayer.stopAudio()
		self._pendingSoundSourcePath = None
		self._selectedSoundFileName = None
		self.soundFileTextCtrl.ChangeValue("")
		self.playSoundBtn.Enable(False)
		self.clearSoundBtn.Enable(False)
		self.soundFileTextCtrl.SetFocus()

	def onClose(self, evt) -> None:
		soundPlayer.stopAudio()
		evt.Skip()

	def onCancel(self, evt) -> None:
		soundPlayer.stopAudio()
		evt.Skip()

	def onOk(self, evt: wx.CommandEvent) -> None:
		soundPlayer.stopAudio()
		if not self.patternTextCtrl.GetValue():
			if gui and hasattr(gui, "messageBox"):
				gui.messageBox(
					_("A pattern is required."),
					_("Dictionary Entry Error"),
					wx.OK | wx.ICON_WARNING,
					self,
				)
			self.patternTextCtrl.SetFocus()
			return

		# Check if an audio file was entered in the text field directly
		enteredSound = self.soundFileTextCtrl.GetValue().strip()
		if enteredSound:
			if os.path.isabs(enteredSound) and os.path.isfile(enteredSound):
				self._pendingSoundSourcePath = enteredSound
				self._selectedSoundFileName = os.path.basename(enteredSound)
			elif self._pendingSoundSourcePath and os.path.basename(self._pendingSoundSourcePath) == enteredSound:
				self._selectedSoundFileName = enteredSound
			elif not self._selectedSoundFileName:
				self._selectedSoundFileName = enteredSound
		else:
			self._selectedSoundFileName = None
			self._pendingSoundSourcePath = None

		# If a new external audio file was selected, copy it to the add-on's sounds directory
		if self._pendingSoundSourcePath:
			try:
				copiedName = soundStorage.copySoundFile(self._pendingSoundSourcePath)
				self._selectedSoundFileName = copiedName
				self._pendingSoundSourcePath = None
			except Exception as e:
				log.exception(f"Error copying sound file: {e}")
				if gui and hasattr(gui, "messageBox"):
					gui.messageBox(
						_("Failed to copy audio file to add-on directory:\n{error}").format(error=e),
						_("Error"),
						wx.OK | wx.ICON_ERROR,
						self,
					)
				return

		entryType = self.getType()
		userComment = self.commentTextCtrl.GetValue()
		fullComment = buildComment(userComment, self._selectedSoundFileName)

		if SpeechDictEntry:
			try:
				dictEntry = self.dictEntry = SpeechDictEntry(
					self.patternTextCtrl.GetValue(),
					self.replacementTextCtrl.GetValue(),
					fullComment,
					bool(self.caseSensitiveCheckBox.GetValue()),
					entryType,
				)
				dictEntry.userComment = userComment
				dictEntry.soundFileName = self._selectedSoundFileName
			except RegexpError as e:
				log.debugWarning(f"Regex error in pattern field: {e}")
				if EntryType and entryType != EntryType.REGEXP:
					raise e
				if gui and hasattr(gui, "messageBox"):
					gui.messageBox(
						_('Regular Expression error in the pattern field: "{error}".').format(error=e),
						_("Dictionary Entry Error"),
						wx.OK | wx.ICON_WARNING,
						self,
					)
				self.patternTextCtrl.SetFocus()
				return

			try:
				with suppressSound():
					dictEntry.sub("test")
			except RegexpError as e:
				log.debugWarning(f"Regex error in replacement field: {e}")
				if EntryType and entryType != EntryType.REGEXP:
					raise e
				if gui and hasattr(gui, "messageBox"):
					gui.messageBox(
						_('Regular Expression error in the replacement field: "{error}".').format(error=e),
						_("Dictionary Entry Error"),
						wx.OK | wx.ICON_WARNING,
						self,
					)
				self.replacementTextCtrl.SetFocus()
				return
		else:
			class DummyEntry:
				pass
			dictEntry = self.dictEntry = DummyEntry()
			dictEntry.pattern = self.patternTextCtrl.GetValue()
			dictEntry.replacement = self.replacementTextCtrl.GetValue()
			dictEntry.comment = fullComment
			dictEntry.caseSensitive = bool(self.caseSensitiveCheckBox.GetValue())
			dictEntry.type = entryType
			dictEntry.userComment = userComment
			dictEntry.soundFileName = self._selectedSoundFileName

		evt.Skip()


_dialogBases = []
if SettingsDialog and SettingsDialog is not object:
	_dialogBases.append(SettingsDialog)
elif wx and hasattr(wx, "Dialog"):
	_dialogBases.append(wx.Dialog)
else:
	_dialogBases.append(object)


class EnhancedDictionaryDialog(
	*_dialogBases,
	metaclass=guiHelper.SIPABCMeta if (guiHelper and hasattr(guiHelper, "SIPABCMeta")) else type,
):
	"""Enhanced Dictionary dialog with Sound column and integrated sound management."""

	helpId = "SpeechDictionaries"

	def __init__(self, parent: Optional[wx.Window], title: str, speechDict: SpeechDict):
		self.title = title
		self.speechDict = speechDict
		self.tempSpeechDict = SpeechDict() if SpeechDict else []
		if speechDict:
			self.tempSpeechDict.extend(self.speechDict)
		if globalVars:
			globalVars.speechDictionaryProcessing = False
		if SettingsDialog and SettingsDialog is not object:
			super().__init__(parent, resizeable=True)
		elif wx and hasattr(wx, "Dialog") and isinstance(self, wx.Dialog):
			wx.Dialog.__init__(self, parent, title=title)
		else:
			super().__init__()
		self.SetSize(660, 520)
		self.CentreOnScreen()

	def makeSettings(self, settingsSizer) -> None:
		sHelper = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		entriesLabelText = _("&Dictionary entries")
		self.dictList = sHelper.addLabeledControl(
			entriesLabelText,
			wx.ListCtrl,
			style=wx.LC_REPORT | wx.LC_SINGLE_SEL,
		)
		self.dictList.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.onEditClick)
		self.dictList.Bind(wx.EVT_CONTEXT_MENU, self.onContextMenu)
		self.dictList.Bind(wx.EVT_CHAR_HOOK, self.onCharHook)

		# Columns: Comment, Pattern, Replacement, Sound, Case, Type
		self.dictList.AppendColumn(_("Comment"), width=130)
		self.dictList.AppendColumn(_("Pattern"), width=130)
		self.dictList.AppendColumn(_("Replacement"), width=130)
		self.dictList.AppendColumn(_("Sound"), width=110)
		self.dictList.AppendColumn(_("case"), width=50)
		self.dictList.AppendColumn(_("Type"), width=60)

		self.offOn = (_("off"), _("on"))
		for entry in self.tempSpeechDict:
			prepareEntry(entry)
			if _originalDictionaryDialog and hasattr(_originalDictionaryDialog, "TYPE_LABELS"):
				typeLabel = _originalDictionaryDialog.TYPE_LABELS.get(entry.type, str(entry.type))
			else:
				typeLabel = str(entry.type)
			self.dictList.Append(
				(
					entry.userComment or "",
					entry.pattern,
					entry.replacement,
					entry.soundFileName or "",
					self.offOn[int(entry.caseSensitive)],
					typeLabel,
				),
			)

		bHelper = guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		bHelper.addButton(parent=self, label=_("&Add")).Bind(wx.EVT_BUTTON, self.onAddClick)
		bHelper.addButton(parent=self, label=_("&Edit")).Bind(wx.EVT_BUTTON, self.onEditClick)
		bHelper.addButton(parent=self, label=_("&Remove")).Bind(wx.EVT_BUTTON, self.onRemoveClick)
		bHelper.sizer.AddStretchSpacer()
		bHelper.addButton(parent=self, label=_("Remove all")).Bind(wx.EVT_BUTTON, self.onRemoveAll)

		sHelper.addItem(bHelper, flag=wx.EXPAND)

	def onCharHook(self, evt: wx.KeyEvent) -> None:
		key = evt.GetKeyCode()
		if key == wx.WXK_DELETE:
			self.onRemoveClick(None)
		else:
			evt.Skip()

	def onContextMenu(self, evt: wx.ContextMenuEvent) -> None:
		menu = wx.Menu()
		editItem = menu.Append(wx.ID_ANY, _("&Edit"))
		removeItem = menu.Append(wx.ID_ANY, _("&Remove"))
		self.Bind(wx.EVT_MENU, self.onEditClick, editItem)
		self.Bind(wx.EVT_MENU, self.onRemoveClick, removeItem)
		self.PopupMenu(menu)
		menu.Destroy()

	def postInit(self) -> None:
		self.dictList.SetFocus()

	def onCancel(self, evt) -> None:
		if globalVars:
			globalVars.speechDictionaryProcessing = True
		super().onCancel(evt)

	def onOk(self, evt) -> None:
		if globalVars:
			globalVars.speechDictionaryProcessing = True
		if self.tempSpeechDict != self.speechDict:
			del self.speechDict[:]
			self.speechDict.extend(self.tempSpeechDict)
			self.speechDict.save()
		super().onOk(evt)

	def onAddClick(self, evt: wx.CommandEvent) -> None:
		entryDialog = EnhancedDictionaryEntryDialog(self, title=_("Add Dictionary Entry"))
		if entryDialog.ShowModal() == wx.ID_OK:
			entry = entryDialog.dictEntry
			self.tempSpeechDict.append(entry)
			if _originalDictionaryDialog and hasattr(_originalDictionaryDialog, "TYPE_LABELS"):
				typeLabel = _originalDictionaryDialog.TYPE_LABELS.get(entry.type, str(entry.type))
			else:
				typeLabel = str(entry.type)
			self.dictList.Append(
				(
					entry.userComment or "",
					entry.pattern,
					entry.replacement,
					entry.soundFileName or "",
					self.offOn[int(entry.caseSensitive)],
					typeLabel,
				),
			)
			index = self.dictList.GetFirstSelected()
			while index >= 0:
				self.dictList.Select(index, on=0)
				index = self.dictList.GetNextSelected(index)
			addedIndex = self.dictList.GetItemCount() - 1
			self.dictList.Select(addedIndex)
			self.dictList.Focus(addedIndex)
			self.dictList.SetFocus()
		entryDialog.Destroy()

	def onEditClick(self, evt: wx.CommandEvent) -> None:
		if self.dictList.GetSelectedItemCount() != 1:
			return
		editIndex = self.dictList.GetFirstSelected()
		if editIndex < 0:
			return

		entry = self.tempSpeechDict[editIndex]
		prepareEntry(entry)

		entryDialog = EnhancedDictionaryEntryDialog(self)
		entryDialog.patternTextCtrl.SetValue(entry.pattern)
		entryDialog.replacementTextCtrl.SetValue(entry.replacement)
		entryDialog.commentTextCtrl.SetValue(entry.userComment or "")
		entryDialog.setSoundFileName(entry.soundFileName)
		entryDialog.caseSensitiveCheckBox.SetValue(entry.caseSensitive)
		entryDialog.setType(entry.type)

		if entryDialog.ShowModal() == wx.ID_OK:
			updatedEntry = entryDialog.dictEntry
			self.tempSpeechDict[editIndex] = updatedEntry
			if _originalDictionaryDialog and hasattr(_originalDictionaryDialog, "TYPE_LABELS"):
				typeLabel = _originalDictionaryDialog.TYPE_LABELS.get(updatedEntry.type, str(updatedEntry.type))
			else:
				typeLabel = str(updatedEntry.type)
			self.dictList.SetItem(editIndex, 0, updatedEntry.userComment or "")
			self.dictList.SetItem(editIndex, 1, updatedEntry.pattern)
			self.dictList.SetItem(editIndex, 2, updatedEntry.replacement)
			self.dictList.SetItem(editIndex, 3, updatedEntry.soundFileName or "")
			self.dictList.SetItem(editIndex, 4, self.offOn[int(updatedEntry.caseSensitive)])
			self.dictList.SetItem(editIndex, 5, typeLabel)
			self.dictList.SetFocus()
		entryDialog.Destroy()

	def onRemoveClick(self, evt) -> None:
		index = self.dictList.GetFirstSelected()
		while index >= 0:
			self.dictList.DeleteItem(index)
			del self.tempSpeechDict[index]
			index = self.dictList.GetNextSelected(index)
		self.dictList.SetFocus()

	def onRemoveAll(self, evt: wx.CommandEvent) -> None:
		if (
			gui.messageBox(
				_("Are you sure you want to remove all the entries in this dictionary?"),
				_("Remove all"),
				style=wx.YES | wx.NO | wx.NO_DEFAULT,
			)
			!= wx.YES
		):
			return
		while self.tempSpeechDict:
			self.dictList.DeleteItem(0)
			del self.tempSpeechDict[0]
		self.dictList.SetFocus()


class EnhancedDefaultDictionaryDialog(EnhancedDictionaryDialog):
	def __init__(self, parent: Optional[wx.Window]):
		definition = speechDictHandler.definitions._getDictionaryDefinition(DictionaryType.DEFAULT)
		super().__init__(
			parent,
			title=definition.displayName,
			speechDict=definition.dictionary,
		)


class EnhancedVoiceDictionaryDialog(EnhancedDictionaryDialog):
	def __init__(self, parent: Optional[wx.Window]):
		definition = speechDictHandler.definitions._getDictionaryDefinition(DictionaryType.VOICE)
		super().__init__(
			parent,
			title=definition.displayName,
			speechDict=definition.dictionary,
		)


class EnhancedTemporaryDictionaryDialog(EnhancedDictionaryDialog):
	def __init__(self, parent: Optional[wx.Window]):
		definition = speechDictHandler.definitions._getDictionaryDefinition(DictionaryType.TEMP)
		super().__init__(
			parent,
			title=definition.displayName,
			speechDict=definition.dictionary,
		)


def patchGui() -> None:
	"""Patch NVDA's dictionary dialog classes with Enhanced versions."""
	global _originalDictionaryEntryDialog, _originalDictionaryDialog
	global _originalDefaultDictionaryDialog, _originalVoiceDictionaryDialog, _originalTemporaryDictionaryDialog
	global _originalGuiDefaultDialog, _originalGuiVoiceDialog, _originalGuiTemporaryDialog

	try:
		import gui.speechDict
	except ImportError:
		return

	if _originalDictionaryEntryDialog is not None:
		return

	# Save originals
	_originalDictionaryEntryDialog = gui.speechDict.DictionaryEntryDialog
	_originalDictionaryDialog = gui.speechDict.DictionaryDialog
	_originalDefaultDictionaryDialog = gui.speechDict.DefaultDictionaryDialog
	_originalVoiceDictionaryDialog = gui.speechDict.VoiceDictionaryDialog
	_originalTemporaryDictionaryDialog = gui.speechDict.TemporaryDictionaryDialog

	_originalGuiDefaultDialog = getattr(gui, "DefaultDictionaryDialog", None)
	_originalGuiVoiceDialog = getattr(gui, "VoiceDictionaryDialog", None)
	_originalGuiTemporaryDialog = getattr(gui, "TemporaryDictionaryDialog", None)

	# Apply enhanced dialogs
	gui.speechDict.DictionaryEntryDialog = EnhancedDictionaryEntryDialog
	gui.speechDict.DictionaryDialog = EnhancedDictionaryDialog
	gui.speechDict.DefaultDictionaryDialog = EnhancedDefaultDictionaryDialog
	gui.speechDict.VoiceDictionaryDialog = EnhancedVoiceDictionaryDialog
	gui.speechDict.TemporaryDictionaryDialog = EnhancedTemporaryDictionaryDialog

	gui.DefaultDictionaryDialog = EnhancedDefaultDictionaryDialog
	gui.VoiceDictionaryDialog = EnhancedVoiceDictionaryDialog
	gui.TemporaryDictionaryDialog = EnhancedTemporaryDictionaryDialog

	log.debug("Patched NVDA dictionary dialogs for Sound Dictionaries")


def unpatchGui() -> None:
	"""Restore NVDA's original dictionary dialog classes."""
	global _originalDictionaryEntryDialog, _originalDictionaryDialog
	global _originalDefaultDictionaryDialog, _originalVoiceDictionaryDialog, _originalTemporaryDictionaryDialog
	global _originalGuiDefaultDialog, _originalGuiVoiceDialog, _originalGuiTemporaryDialog

	if _originalDictionaryEntryDialog is None:
		return

	try:
		import gui.speechDict
	except ImportError:
		return

	gui.speechDict.DictionaryEntryDialog = _originalDictionaryEntryDialog
	gui.speechDict.DictionaryDialog = _originalDictionaryDialog
	gui.speechDict.DefaultDictionaryDialog = _originalDefaultDictionaryDialog
	gui.speechDict.VoiceDictionaryDialog = _originalVoiceDictionaryDialog
	gui.speechDict.TemporaryDictionaryDialog = _originalTemporaryDictionaryDialog

	if _originalGuiDefaultDialog:
		gui.DefaultDictionaryDialog = _originalGuiDefaultDialog
	if _originalGuiVoiceDialog:
		gui.VoiceDictionaryDialog = _originalGuiVoiceDialog
	if _originalGuiTemporaryDialog:
		gui.TemporaryDictionaryDialog = _originalGuiTemporaryDialog

	_originalDictionaryEntryDialog = None
	_originalDictionaryDialog = None
	_originalDefaultDictionaryDialog = None
	_originalVoiceDictionaryDialog = None
	_originalTemporaryDictionaryDialog = None
	_originalGuiDefaultDialog = None
	_originalGuiVoiceDialog = None
	_originalGuiTemporaryDialog = None

	log.debug("Restored NVDA dictionary dialogs")
