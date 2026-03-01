import hashlib
from pathlib import Path
import pytest

from kikx.lib.hash import hash_file


# ----------------------------------
# Test: hash matches known content
# ----------------------------------

def test_hash_file_known_content(tmp_path):
  file_path = tmp_path / "test.txt"
  content = b"hello world"
  file_path.write_bytes(content)

  expected_hash = hashlib.sha256(content).hexdigest()

  assert hash_file(file_path) == expected_hash


# ----------------------------------
# Test: empty file hash
# ----------------------------------

def test_hash_empty_file(tmp_path):
  file_path = tmp_path / "empty.txt"
  file_path.write_bytes(b"")

  expected_hash = hashlib.sha256(b"").hexdigest()

  assert hash_file(file_path) == expected_hash


# ----------------------------------
# Test: custom chunk size
# ----------------------------------

def test_hash_file_custom_chunk_size(tmp_path):
  file_path = tmp_path / "big.txt"
  content = b"a" * (1024 * 2)  # 2KB
  file_path.write_bytes(content)

  expected_hash = hashlib.sha256(content).hexdigest()

  assert hash_file(file_path, chunk_size=512) == expected_hash


# ----------------------------------
# Test: file not found
# ----------------------------------

def test_hash_file_not_found(tmp_path):
  file_path = tmp_path / "does_not_exist.txt"

  with pytest.raises(FileNotFoundError):
    hash_file(file_path)