"""
verify_install.py — Dependency verification script for LexAssist AI.

Run this after pip install -r requirements.txt to confirm every package
is importable and meets the minimum required version.

Usage:
    python verify_install.py
"""

import sys
import importlib
from importlib.metadata import version, PackageNotFoundError

# (import_name, pip_package_name, minimum_version)
REQUIRED = [
    ("langgraph",             "langgraph",             "0.2.0"),
    ("langchain",             "langchain",             "0.3.0"),
    ("langchain_openai",      "langchain-openai",      "0.2.0"),
    ("langchain_community",   "langchain-community",   "0.3.0"),
    ("chromadb",              "chromadb",              "0.5.0"),
    ("sentence_transformers", "sentence-transformers", "3.0.0"),
    ("streamlit",             "streamlit",             "1.40.0"),
    ("ragas",                 "ragas",                 "0.2.0"),
    ("yaml",                  "PyYAML",                "6.0"),
    ("dotenv",                "python-dotenv",         "1.0.0"),
    ("pytest",                "pytest",                "8.0.0"),
]

# ── Version comparison helper ─────────────────────────────────────────────────

def parse_version(v: str) -> tuple:
    """Convert '1.2.3' to (1, 2, 3) for numeric comparison."""
    try:
        return tuple(int(x) for x in v.split(".")[:3])
    except ValueError:
        return (0,)


def check_version(pkg_name: str, minimum: str) -> tuple[str, bool]:
    """Return (installed_version, meets_minimum)."""
    try:
        installed = version(pkg_name)
        meets = parse_version(installed) >= parse_version(minimum)
        return installed, meets
    except PackageNotFoundError:
        return "NOT FOUND", False


# ── Main check ────────────────────────────────────────────────────────────────

def main() -> int:
    print(f"Python {sys.version}")
    print(f"Checking {len(REQUIRED)} packages...\n")

    header = f"{'Package':<28} {'Installed':<12} {'Required':<12} {'Status'}"
    print(header)
    print("-" * len(header))

    failures = []

    for import_name, pip_name, minimum in REQUIRED:
        # 1. Can we import it?
        try:
            importlib.import_module(import_name)
        except ImportError as e:
            print(f"  {'IMPORT ERROR':<26} {pip_name:<28} — {e}")
            failures.append(pip_name)
            continue

        # 2. Does the installed version meet the minimum?
        installed_ver, ok = check_version(pip_name, minimum)
        status = "OK" if ok else "TOO OLD"
        flag = "" if ok else "  <-- UPGRADE NEEDED"
        print(f"  {pip_name:<28} {installed_ver:<12} >={minimum:<9} {status}{flag}")

        if not ok:
            failures.append(pip_name)

    print()

    # ── LangGraph deep-import check ───────────────────────────────────────────
    print("Deep import checks:")
    deep_checks = [
        ("langgraph.graph",           "StateGraph"),
        ("langgraph.checkpoint.memory","MemorySaver"),
        ("langchain_openai",          "ChatOpenAI"),
        ("langchain_community.vectorstores", "Chroma"),
        ("langchain_community.embeddings",   "HuggingFaceEmbeddings"),
        # LangChain 0.3+: splitters moved to langchain_text_splitters
        ("langchain_text_splitters",  "RecursiveCharacterTextSplitter"),
        # LangChain 0.3+: Document lives in langchain_core
        ("langchain_core.documents",  "Document"),
    ]

    for module, attr in deep_checks:
        try:
            mod = importlib.import_module(module)
            getattr(mod, attr)
            print(f"  {module}.{attr:<35} OK")
        except (ImportError, AttributeError) as e:
            print(f"  {module}.{attr:<35} FAIL — {e}")
            failures.append(f"{module}.{attr}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    if failures:
        print(f"FAILED ({len(failures)} issue(s)):")
        for f in failures:
            print(f"  - {f}")
        print("\nFix: pip install -r requirements.txt --upgrade")
        return 1
    else:
        print("All dependencies verified. You are ready to build.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
