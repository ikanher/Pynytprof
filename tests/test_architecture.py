from pathlib import Path
import pkgutil
import re

DOC = Path("docs/architecture.md")


def test_architecture_doc_headings():
    text = DOC.read_text(encoding="utf-8")
    assert text.startswith("# Architecture"), "missing H1"
    for head in ["## Component map", "## Runtime flow", "## Extensibility"]:
        assert head in text


def test_component_map_mentions_packages():
    text = DOC.read_text(encoding="utf-8")
    component = text.split("## Component map", 1)[1].split("##", 1)[0]
    packages = [m.name for m in pkgutil.iter_modules(["src/pynytprof"]) if not m.name.startswith("_")]
    for name in packages:
        assert name in component
