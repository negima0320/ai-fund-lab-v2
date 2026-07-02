from __future__ import annotations

import plistlib
from pathlib import Path


def test_launchd_operations_plists_are_demo_only_and_do_not_include_production_unlock_or_secrets():
    launchd_dir = Path("tools/launchd")
    plist_names = [
        path.name for path in launchd_dir.glob("com.aifundlab.operations.*.plist")
    ]
    assert "com.aifundlab.operations.demo_submit.plist" in plist_names
    assert "com.aifundlab.operations.demo_special_fill.plist" in plist_names
    assert "com.aifundlab.operations.auto_approval.plist" in plist_names
    for name in plist_names:
        payload = plistlib.loads((launchd_dir / name).read_bytes())
        rendered = str(payload).lower()
        assert "production_unlock" not in rendered
        assert "production_order_allowed=true" not in rendered
        assert "second_password_file" not in rendered
        assert "second-password-file" not in rendered
        assert "secret" not in rendered
        assert "private_key" not in rendered
        assert payload.get("EnvironmentVariables", {}).get("TACHIBANA_API_ENV") == "demo"
