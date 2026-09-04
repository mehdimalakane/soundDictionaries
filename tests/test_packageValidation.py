# Unit tests for .nvda-addon package verification
import unittest
import os
import zipfile
from configobj import ConfigObj


class TestPackageValidation(unittest.TestCase):

	def setUp(self):
		self.bundlePath = os.path.abspath(
			os.path.join(os.path.dirname(__file__), "..", "soundDictionaries-1.0.0.nvda-addon")
		)

	def test_bundleExists(self):
		self.assertTrue(os.path.isfile(self.bundlePath), f"Add-on bundle not found at {self.bundlePath}")

	def test_bundleArchiveStructure(self):
		with zipfile.ZipFile(self.bundlePath, "r") as zf:
			namelist = zf.namelist()

			# 1. manifest.ini must be at archive root
			self.assertIn("manifest.ini", namelist)

			# 2. Global plugin files must be present
			expectedFiles = [
				"globalPlugins/soundDictionaries/__init__.py",
				"globalPlugins/soundDictionaries/soundStorage.py",
				"globalPlugins/soundDictionaries/soundPlayer.py",
				"globalPlugins/soundDictionaries/dictionaryEntry.py",
				"globalPlugins/soundDictionaries/speechExtension.py",
				"globalPlugins/soundDictionaries/guiExtension.py",
				"doc/en/readme.html",
				"sounds/.gitkeep",
			]
			# Normalize separators in zip namelist
			normList = [name.replace("\\", "/") for name in namelist]
			for ef in expectedFiles:
				self.assertIn(ef, normList, f"Missing file in add-on package: {ef}")

			# 3. Ensure no compiled python cache files are in the bundle
			for name in normList:
				self.assertFalse(name.endswith(".pyc"), f"Found .pyc file in bundle: {name}")
				self.assertFalse("__pycache__" in name, f"Found __pycache__ in bundle: {name}")

			# 4. Validate manifest within archive
			with zf.open("manifest.ini") as mf:
				manifest = ConfigObj(mf.read().decode("utf-8").splitlines())
				self.assertEqual(manifest["name"], "soundDictionaries")
				self.assertEqual(manifest["version"], "1.0.0")
				self.assertTrue(manifest["minimumNVDAVersion"].startswith("2024."))


if __name__ == "__main__":
	unittest.main()
