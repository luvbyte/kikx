import pytest

from kikx.lib.utils import is_version_ok, is_version_supported, is_update_available
from packaging.version import Version, InvalidVersion



def test_within_range():
  assert is_version_supported("0.2.3", "0.2", "0.2.5") is True


def test_below_min():
  assert is_version_supported("0.1.9", "0.2", "0.3") is False


def test_above_max():
  assert is_version_supported("0.3.1", "0.2", "0.3") is False


def test_equal_to_min():
  assert is_version_supported("0.2", "0.2", "0.5") is True


def test_equal_to_max():
  assert is_version_supported("0.5", "0.2", "0.5") is True


def test_min_only_valid():
  assert is_version_supported("1.5", "1.0", None) is True


def test_min_only_invalid():
  assert is_version_supported("0.9", "1.0", None) is False


def test_max_only_valid():
  assert is_version_supported("0.2", None, "0.3") is True


def test_max_only_invalid():
  assert is_version_supported("0.4", None, "0.3") is False


def test_no_limits():
  assert is_version_supported("10.5") is True


def test_invalid_target_version():
  assert is_version_supported("abc", "1.0", "2.0") is False

# =========================
# Tests for is_version_ok
# =========================

@pytest.mark.parametrize(
  "current, requirement, expected",
  [
    ("1.2.3", ">=1.2.0", True),
    ("1.2.3", ">1.2.3", False),
    ("1.2.3", "<2.0", True),
    ("1.2.3", "<=1.2.3", True),
    ("1.2.3", "==1.2.3", True),
    ("1.2.3", "==1.2.4", False),
    ("1.5.0", ">=1.2,<2.0", True),
    ("2.0.0", ">=1.2,<2.0", False),
    ("1.2.3rc1", ">=1.2.3", False),  # prerelease case
  ],
)
def test_is_version_ok_valid_cases(current, requirement, expected):
  assert is_version_ok(current, requirement) is expected


@pytest.mark.parametrize(
  "current, requirement",
  [
    ("invalid", ">=1.2.0"),
    ("1.2.3", "invalid"),
    ("1.2.x", ">=1.2.0"),
  ],
)
def test_is_version_ok_invalid_inputs(current, requirement):
  assert is_version_ok(current, requirement) is False


# =========================
# Tests for is_update_available
# =========================

@pytest.mark.parametrize(
  "current, latest, expected",
  [
    ("1.2.3", "1.2.4", True),
    ("1.2.3", "1.3.0", True),
    ("1.2.3", "2.0.0", True),
    ("1.2.3", "1.2.3", False),
    ("1.2.4", "1.2.3", False),
    ("2.0.0", "1.9.9", False),
    ("1.2.3rc1", "1.2.3", True),  # prerelease upgrade
  ],
)
def test_is_update_available_valid_cases(current, latest, expected):
  assert is_update_available(current, latest) is expected


@pytest.mark.parametrize(
  "current, latest",
  [
    ("invalid", "1.2.3"),
    ("1.2.3", "invalid"),
    ("1.2.x", "1.2.3"),
  ],
)

def test_is_update_available_invalid_inputs(current, latest):
  assert is_update_available(current, latest) is False
