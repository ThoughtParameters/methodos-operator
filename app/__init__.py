import os
import asyncio
import aiofiles
import json
import hashlib
import tarfile
import shutil
import logging
import datetime
import pytz

from pathlib import Path as PyPath

from typing import List, Optional, Dict, Any, Literal

# -- Global App Objects ---
APP_NAME: Literal["methodos-operator"] = "methodos-operator"
APP_VERSION: Literal["1.0.0"] = "1.0.0"
APP_DESCRIPTION: str = """Methodos Operator serves as the central nervous system and primary server component within the Methodos configuration management suite.
True to its name, derived from the Greek "methodos" (meaning a systematic way, method, or pursuit of knowledge) and the Latin "operator" (a worker or one who performs an operation),
the Methodos Operator is engineered to systematically manage, enforce, and oversee the desired state of your entire IT infrastructure.
"""
APP_AUTHOR: str = "Thought Parameters LLC"
APP_LICENSE: str = "MIT"
APP_CONTACT: Dict[str, str] = {
  "name": "Team Imperium",
  "url": "https://methodos-imperium.thoughtparameters.com",
  "email": "methodos.imperium@thoughtparameters.com",
}

# -- Global Path Objects (resolved at startup) ---
# Ensure these are absolute paths for reliability
TMP_DIR: str = "tmp_uploads/"
BOOKS_DIR: str = "books/"
INDEX_FILE: str = "index.json"

# -- Global logging objects ---
logger = logging.getLogger(APP_NAME)
logger.setLevel(logging.INFO)
if not logger.hasHandlers(): # Avoid adding multiple handlers if module is reloaded
  formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
  ch = logging.StreamHandler()
  ch.setLevel(logging.INFO)
  ch.setFormatter(formatter)
  logger.addHandler(ch)




# -- Global variables ---
# These are initialized at startup
# and should not be modified directly
# They are meant to be accessed via the provided functions
# and methods in this module


def calculate_sha256(filepath: str) -> str:
  """Calculates the SHA256 checksum of a file."""
  sha256_hash = hashlib.sha256()
  with open(filepath, "rb") as f:
    # Read and update hash string vaule in blocks of 4K
    for byte_block in iter(lambda: f.read(4096), b""):
      sha256_hash.update(byte_block)
  return sha256_hash.hexdigest()  
  
def calculate_dir_checksum(dir_path: str, hash_algo: str = "sha256") -> str:
  """Calculates the checksum of a directory."""
  hasher = hashlib.new(hash_algo)
  
  for root, _, files in sorted(os.walk(dir_path)):
    for filename in sorted(files):
      filepath = os.path.join(root, filename)
      realtive_path = os.path.relpath(filepath, dir_path)
      hasher.update(realtive_path.encode('utf-8'))
      with open(filepath, "rb") as f:
        while True:
          chunk = f.read(4096)
          if not chunk:
            break
          hasher.update(chunk)
  
  return hasher.hexdigest()