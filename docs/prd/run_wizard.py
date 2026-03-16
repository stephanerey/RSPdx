from pathlib import Path
import runpy
import sys


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    wizard_path = repo_root / "prd_library" / "tools" / "project_intake_wizard" / "wizard.py"
    if not wizard_path.exists():
        raise FileNotFoundError(f"Wizard not found: {wizard_path}")

    sys.argv[0] = str(wizard_path)
    runpy.run_path(str(wizard_path), run_name="__main__")


if __name__ == "__main__":
    main()
