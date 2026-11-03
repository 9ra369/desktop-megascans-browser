import json
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures" / "manifests"

# 設計: カタログのファイル一覧は JSON の構造ごとに別のキーに入っている。
CATALOG_KEYS = {
    "surface": ("maps",),
    "3d": ("components", "meshes"),
    "3dplant": ("maps", "billboards", "models"),
}


def load_manifest(asset_id: str) -> dict:
    return json.loads((FIXTURES / f"{asset_id}.json").read_text(encoding="utf-8"))


def catalog_entries(manifest: dict) -> list[dict]:
    """カタログに載っているファイルの要素を、親の resolution 付きで平坦に返す。"""
    entries: list[dict] = []

    def walk(node: object, resolution: str | None) -> None:
        if isinstance(node, dict):
            resolution = node.get("resolution", resolution)
            if isinstance(node.get("uri"), str):
                entries.append({"uri": node["uri"], "resolution": resolution})
                return
            for value in node.values():
                walk(value, resolution)
        elif isinstance(node, list):
            for value in node:
                walk(value, resolution)

    for key in CATALOG_KEYS[manifest["categories"][0]]:
        walk(manifest[key], None)
    return entries
