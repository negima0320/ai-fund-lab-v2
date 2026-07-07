import ast
from pathlib import Path


RUNTIME_ROOT = Path("src/ai_fund_lab_v2/runtime_v2")
RUNTIME_PREFIX = "ai_fund_lab_v2.runtime_v2"

FORBIDDEN_IMPORTS = {
    "runtime_v2.report": (
        "ai_fund_lab_v2.runtime_v2.asset.writer",
        "ai_fund_lab_v2.runtime_v2.pending.writer",
        "ai_fund_lab_v2.broker",
        "ai_fund_lab_v2.runtime_v2.submit",
    ),
    "runtime_v2.audit": (
        "ai_fund_lab_v2.broker",
        "ai_fund_lab_v2.runtime_v2.submit",
    ),
    "runtime_v2.reconcile": (
        "ai_fund_lab_v2.runtime_v2.asset.writer",
        "ai_fund_lab_v2.runtime_v2.pending.writer",
    ),
    "runtime_v2.planning": (
        "ai_fund_lab_v2.broker",
        "ai_fund_lab_v2.runtime_v2.submit",
    ),
    "runtime_v2.approval": (
        "ai_fund_lab_v2.broker",
        "ai_fund_lab_v2.runtime_v2.submit",
    ),
    "runtime_v2.notification.payload": (
        "ai_fund_lab_v2.runtime_v2.notification.sender",
        "ai_fund_lab_v2.runtime_v2.notification.send",
        "ai_fund_lab_v2.broker",
    ),
    "runtime_v2": (
        "ai_fund_lab_v2.runtime.",
        "ai_fund_lab_v2.operations.",
        "ai_fund_lab_v2.workflow",
        "ai_fund_lab_v2.entrypoint",
    ),
}


def test_runtime_v2_import_graph_has_no_obvious_cycles():
    graph = _runtime_import_graph()

    cycle = _find_cycle(graph)

    assert cycle == (), " -> ".join(cycle)


def test_report_audit_reconcile_do_not_import_current_writers_or_submit_paths():
    imports = _imports_by_module()

    _assert_no_forbidden_imports(imports, "runtime_v2.report")
    _assert_no_forbidden_imports(imports, "runtime_v2.audit")
    _assert_no_forbidden_imports(imports, "runtime_v2.reconcile")


def test_planning_approval_do_not_import_broker_api_or_submit_runtime():
    imports = _imports_by_module()

    _assert_no_forbidden_imports(imports, "runtime_v2.planning")
    _assert_no_forbidden_imports(imports, "runtime_v2.approval")


def test_notification_payload_does_not_import_notification_sender():
    imports = _imports_by_module()

    _assert_no_forbidden_imports(imports, "runtime_v2.notification.payload")


def test_runtime_v2_modules_do_not_import_legacy_workflow_or_entrypoint():
    imports = _imports_by_module()

    _assert_no_forbidden_imports(imports, "runtime_v2")


def _imports_by_module() -> dict[str, tuple[str, ...]]:
    return {
        _module_name(path): tuple(sorted(_extract_imports(path)))
        for path in sorted(RUNTIME_ROOT.rglob("*.py"))
    }


def _runtime_import_graph() -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {}
    for module, imports in _imports_by_module().items():
        graph[module] = {
            imported
            for imported in imports
            if imported == RUNTIME_PREFIX or imported.startswith(f"{RUNTIME_PREFIX}.")
        }
    return graph


def _extract_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def _module_name(path: Path) -> str:
    relative = path.relative_to(RUNTIME_ROOT).with_suffix("")
    parts = ("ai_fund_lab_v2", "runtime_v2", *relative.parts)
    return ".".join(parts)


def _assert_no_forbidden_imports(imports_by_module: dict[str, tuple[str, ...]], scope: str) -> None:
    forbidden = FORBIDDEN_IMPORTS[scope]
    for module, imports in imports_by_module.items():
        if not _module_in_scope(module, scope):
            continue
        for imported in imports:
            assert not any(imported == item or imported.startswith(f"{item}.") for item in forbidden), (
                f"{module} imports forbidden dependency {imported!r}"
            )


def _module_in_scope(module: str, scope: str) -> bool:
    suffix = scope.removeprefix("runtime_v2")
    full_scope = f"{RUNTIME_PREFIX}{suffix}"
    return module == full_scope or module.startswith(f"{full_scope}.")


def _find_cycle(graph: dict[str, set[str]]) -> tuple[str, ...]:
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []

    def visit(module: str) -> tuple[str, ...]:
        if module in visiting:
            cycle_start = stack.index(module)
            return tuple((*stack[cycle_start:], module))
        if module in visited:
            return ()
        visiting.add(module)
        stack.append(module)
        for dependency in sorted(graph.get(module, ())):
            cycle = visit(dependency)
            if cycle:
                return cycle
        stack.pop()
        visiting.remove(module)
        visited.add(module)
        return ()

    for module in sorted(graph):
        cycle = visit(module)
        if cycle:
            return cycle
    return ()

