import pytest

from helpers import load_manifest


@pytest.fixture(params=["wlrvaf3", "xiwcfassc", "wfypejzha"])
def manifest(request: pytest.FixtureRequest) -> dict:
    return load_manifest(request.param)
