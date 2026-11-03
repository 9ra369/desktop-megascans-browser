from megascans_browser.core.fingerprint import FileEntry, compute_fingerprint


def entry(rel_path: str, size: int = 10, mtime_ns: int = 1) -> FileEntry:
    return FileEntry(rel_path=rel_path, size=size, mtime_ns=mtime_ns)


def test_fingerprint_is_stable() -> None:
    files = [entry("a.jpg"), entry("b/c.exr", size=20, mtime_ns=5)]
    assert compute_fingerprint(files) == compute_fingerprint(files)


def test_fingerprint_ignores_the_order_of_the_files() -> None:
    a, b = entry("a.jpg"), entry("b/c.exr", size=20, mtime_ns=5)
    assert compute_fingerprint([a, b]) == compute_fingerprint([b, a])


def test_fingerprint_treats_backslashes_as_separators() -> None:
    assert compute_fingerprint([entry(r"b\c.exr")]) == compute_fingerprint([entry("b/c.exr")])


def test_fingerprint_changes_with_the_size() -> None:
    assert compute_fingerprint([entry("a.jpg", size=1)]) != compute_fingerprint(
        [entry("a.jpg", size=2)]
    )


def test_fingerprint_changes_with_the_modified_time() -> None:
    assert compute_fingerprint([entry("a.jpg", mtime_ns=1)]) != compute_fingerprint(
        [entry("a.jpg", mtime_ns=2)]
    )


def test_fingerprint_changes_with_the_path() -> None:
    assert compute_fingerprint([entry("a.jpg")]) != compute_fingerprint([entry("b.jpg")])


def test_fingerprint_of_no_files_is_not_empty() -> None:
    assert compute_fingerprint([])


def test_fingerprint_is_a_sha256_hex_digest() -> None:
    value = compute_fingerprint([entry("a.jpg")])
    assert len(value) == 64
    assert set(value) <= set("0123456789abcdef")


def test_fingerprint_does_not_depend_on_the_absolute_path() -> None:
    # 設計: 元にするのは相対パスだけ。絶対パスは除外する。
    files = [entry("Textures/Atlas/x_4K_Albedo.jpg"), entry("x.json", size=99)]

    assert compute_fingerprint(files) == compute_fingerprint(files)
    assert compute_fingerprint(files) != compute_fingerprint(
        [entry("D:/Megascans/Downloaded/Textures/Atlas/x_4K_Albedo.jpg"), entry("x.json", size=99)]
    )
