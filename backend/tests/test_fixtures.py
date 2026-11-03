import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "manifests"


@pytest.mark.parametrize(
    ("asset_id", "asset_type"),
    [("wlrvaf3", "surface"), ("xiwcfassc", "3d"), ("wfypejzha", "3dplant")],
)
def test_manifest_fixture_matches_its_file_name(asset_id: str, asset_type: str) -> None:
    manifest = json.loads((FIXTURES / f"{asset_id}.json").read_text(encoding="utf-8"))

    assert manifest["id"] == asset_id
    assert manifest["categories"][0] == asset_type
