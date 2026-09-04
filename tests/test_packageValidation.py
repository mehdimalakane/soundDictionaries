# Unit tests for .nvda-addon package verification
import unittest
import os
import zipfile
try:
	from configobj import ConfigObj
except ImportError:
	def ConfigObj(path_or_stream, encoding="utf-8"):
		if hasattr(path_or_stream, "read"):
			lines = path_or_stream.read().decode(encoding).splitlines()
		elif isinstance(path_or_stream, list):
			lines = path_or_stream
		else:
			with open(path_or_stream, "r", encoding=encoding) as f:
				lines = f.readlines()
		d = {}
		for line in lines:
			line = line.strip()
			if line and not line.startswith("#") and "=" in line:
				k, v = line.split("=", 1)
				k = k.strip()
				v = v.strip().strip('"').strip("'")
				d[k] = v
		return d


class TestPackageValidation(unittest.TestCase):

	def setUp(self):
		self.bundlePath = os.path.abspath(
			os.path.join(os.path.dirname(__file__), "..", "soundDictionaries-1.0.0.nvda-addon")
		)
		if not os.path.isfile(self.bundlePath):
			import subprocess
			import sys
			buildScript = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "build_addon.py"))
			subprocess.run([sys.executable, buildScript], check=True, cwd=os.path.dirname(buildScript))

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
