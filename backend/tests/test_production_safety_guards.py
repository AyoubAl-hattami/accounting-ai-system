from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_public_demo_launcher_refuses_inherited_production_environment():
    script = (REPOSITORY_ROOT / "scripts" / "start-public-demo.ps1").read_text(
        encoding="utf-8"
    )
    assert "$env:APP_ENV" in script
    assert "forbidden when APP_ENV=production" in script
    assert script.index("forbidden when APP_ENV=production") < script.index(
        '$env:APP_ENV = "development"'
    )


def test_deprecated_restore_helper_is_blocked_in_production():
    script = (REPOSITORY_ROOT / "backend" / "restore_admin.py").read_text(
        encoding="utf-8"
    )
    assert '== "production"' in script
    assert "forbidden" in script
    assert "bootstrap_platform_admin.py" in script


def test_local_mutation_scripts_have_environment_guards():
    scripts = {
        "seed_demo_data.py": "is_production_environment",
        "cleanup_local_demo_data.py": "APP_ENV=development",
        "reset_company_data.py": "APP_ENV=development",
    }
    for filename, guard in scripts.items():
        content = (REPOSITORY_ROOT / "backend" / "scripts" / filename).read_text(
            encoding="utf-8"
        )
        assert guard in content, filename
