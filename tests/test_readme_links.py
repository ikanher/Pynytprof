from pathlib import Path
import re


def test_readme_has_architecture_link():
    text = Path("README.md").read_text(encoding="utf-8")
    m = re.search(r"\(docs/architecture.md\)", text)
    assert m, "README should link to docs/architecture.md"
    link = Path(m.group(0).strip("()"))
    assert link.is_file()
