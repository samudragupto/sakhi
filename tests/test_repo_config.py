"""Tests verifying repository configuration files."""

import tomllib
from pathlib import Path

import pytest
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent


def test_no_vercel_files_exist() -> None:
    """Ensure no Vercel artifacts remain in the repository."""
    assert not (BASE_DIR / "vercel.json").exists()
    assert not (BASE_DIR / ".vercelignore").exists()
    assert not (BASE_DIR / "api" / "index.py").exists()


def test_requirements_sync_with_pyproject() -> None:
    """Verify requirements.txt is perfectly synced with pyproject.toml runtime deps."""
    req_file = BASE_DIR / "requirements.txt"
    assert req_file.exists(), "requirements.txt must exist"

    # Parse requirements.txt
    req_lines = req_file.read_text(encoding="utf-8").splitlines()
    req_deps = [line.strip() for line in req_lines if line.strip() and not line.startswith("#")]

    # Parse pyproject.toml
    pyproject_file = BASE_DIR / "pyproject.toml"
    assert pyproject_file.exists(), "pyproject.toml must exist"
    
    with open(pyproject_file, "rb") as f:
        data = tomllib.load(f)
        
    pyproject_deps = data.get("project", {}).get("dependencies", [])
    
    assert set(req_deps) == set(pyproject_deps), "Dependencies out of sync!"


def test_ci_workflow_has_required_jobs() -> None:
    """Verify GitHub Actions CI workflow contains all required stages."""
    ci_file = BASE_DIR / ".github" / "workflows" / "ci.yml"
    assert ci_file.exists(), "CI workflow must exist"

    with open(ci_file, "r", encoding="utf-8") as f:
        workflow = yaml.safe_load(f)

    jobs = workflow.get("jobs", {})
    required_jobs = {"lint", "test", "security", "docker", "deploy"}
    
    assert required_jobs.issubset(set(jobs.keys())), "Missing required CI jobs"
    
    # Verify coverage threshold in test job
    test_steps = jobs["test"]["steps"]
    coverage_cmd = next((step["run"] for step in test_steps if "pytest --cov" in step.get("run", "")), "")
    assert "--cov-fail-under=90" in coverage_cmd, "Coverage threshold must be 90%"
