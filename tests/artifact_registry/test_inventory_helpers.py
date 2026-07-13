from pathlib import Path

from ai_fund_lab_v2.artifact_registry.inventory import directory_inventory, sha256_file, stable_json_hash


def test_sha256_file_is_stable(tmp_path: Path) -> None:
    target = tmp_path / "artifact.txt"
    target.write_text("artifact\n", encoding="utf-8")

    assert sha256_file(target) == sha256_file(target)


def test_directory_inventory_changes_with_content(tmp_path: Path) -> None:
    root = tmp_path / "dir"
    root.mkdir()
    child = root / "a.txt"
    child.write_text("a", encoding="utf-8")
    first_hash, first_count, first_size = directory_inventory(root)

    child.write_text("b", encoding="utf-8")
    second_hash, second_count, second_size = directory_inventory(root)

    assert first_count == second_count == 1
    assert first_size == second_size == 1
    assert first_hash != second_hash


def test_stable_json_hash_ignores_key_order() -> None:
    assert stable_json_hash({"b": 2, "a": 1}) == stable_json_hash({"a": 1, "b": 2})
