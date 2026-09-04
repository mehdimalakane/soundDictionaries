#!/usr/bin/env python3
"""Build script to package the Sound Dictionaries add-on into a ready-to-install .nvda-addon file."""

import os
import zipfile
from configobj import ConfigObj


def buildAddon():
	baseDir = os.path.dirname(os.path.abspath(__file__))
	addonDir = os.path.join(baseDir, "soundDictionaries")
	manifestPath = os.path.join(addonDir, "manifest.ini")

	if not os.path.isfile(manifestPath):
		raise FileNotFoundError(f"manifest.ini not found at {manifestPath}")

	manifest = ConfigObj(manifestPath, encoding="utf-8")
	name = manifest["name"]
	version = manifest["version"]
	bundleName = f"{name}-{version}.nvda-addon"
	bundlePath = os.path.join(baseDir, bundleName)

	print(f"Building {bundleName} from {addonDir}...")

	# Remove existing bundle if present
	if os.path.exists(bundlePath):
		os.remove(bundlePath)

	excludeDirs = {"__pycache__", ".pytest_cache"}
	excludeExts = {".pyc", ".pyo"}

	with zipfile.ZipFile(bundlePath, "w", zipfile.ZIP_DEFLATED) as zf:
		for root, dirs, files in os.walk(addonDir):
			# Filter out cache directories in-place
			dirs[:] = [d for d in dirs if d not in excludeDirs]
			for f in sorted(files):
				_, ext = os.path.splitext(f)
				if ext in excludeExts:
					continue
				fullPath = os.path.join(root, f)
				relPath = os.path.relpath(fullPath, addonDir)
				print(f"  Adding: {relPath}")
				zf.write(fullPath, relPath)

	print(f"\nSuccessfully created NVDA add-on package: {bundlePath}")
	print(f"File size: {os.path.getsize(bundlePath)} bytes")
	return bundlePath


if __name__ == "__main__":
	buildAddon()
