from pathlib import Path

from ai_fund_lab_v2.runtime import RuntimePaths


def test_runtime_paths_create_expected_directories(tmp_path: Path) -> None:
    paths = RuntimePaths(runtime_dir=tmp_path / "runtime")

    paths.ensure_base_dirs()

    assert paths.raw_data.is_dir()
    assert paths.raw_normalized_data.is_dir()
    assert paths.feature_data.is_dir()
    assert paths.label_data.is_dir()
    assert paths.logs.is_dir()
    assert paths.cache.is_dir()
    assert paths.reports.is_dir()
    assert paths.tmp.is_dir()
    assert all(str(path).startswith(str(tmp_path)) for path in paths.iter_base_dirs())
