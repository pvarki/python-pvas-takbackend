"""Package level tests"""
from takbackend import __version__


def test_version() -> None:
    """Make sure version matches expected"""
    assert __version__ == "0.1.0"
