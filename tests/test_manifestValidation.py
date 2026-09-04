# Unit tests for manifest validation
import unittest
import os
from configobj import ConfigObj


class TestManifestValidation(unittest.TestCase):

	def setUp(self):
		self.manifestPath = os.path.abspath(
			os.path.join(os.path.dirname(__file__), "..", "soundDictionaries", "manifest.ini")
		)

	def test_manifestFileExists(self):
		self.assertTrue(os.path.isfile(self.manifestPath), f"manifest.ini not found at {self.manifestPath}")

	def test_manifestParsesCleanly(self):
		cfg = ConfigObj(self.manifestPath, encoding="utf-8")
		self.assertIsNotNone(cfg)

		requiredFields = [
			"name",
			"summary",
			"version",
			"description",
			"author",
			"minimumNVDAVersion",
			"lastTestedNVDAVersion",
		]
		for f in requiredFields:
			self.assertIn(f, cfg, f"Missing required manifest field: {f}")
			self.assertTrue(bool(cfg[f]), f"Manifest field '{f}' is empty")

		# Check name convention (lowerCamelCase or alphanumeric)
		self.assertEqual(cfg["name"], "soundDictionaries")

		# Check versions
		minVer = cfg["minimumNVDAVersion"]
		lastVer = cfg["lastTestedNVDAVersion"]
		self.assertTrue(minVer.startswith("2024."))
		self.assertTrue(lastVer.startswith("2026."))

		# Doc file
		if "docFileName" in cfg:
			docPath = os.path.join(os.path.dirname(self.manifestPath), "doc", "en", cfg["docFileName"])
			self.assertTrue(os.path.isfile(docPath), f"Documentation file {docPath} does not exist")


if __name__ == "__main__":
	unittest.main()
