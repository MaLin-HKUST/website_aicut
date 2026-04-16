from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent.parent


def test_worker_build_script_dry_run_reports_versioned_archive(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            "bash",
            str(ROOT / "worker/build.sh"),
        ],
        cwd=ROOT,
        env={
            "PATH": str(Path("/usr/bin")) + ":" + str(Path("/bin")) + ":" + str(Path("/usr/sbin")) + ":" + str(Path("/sbin")),
            "VERSION": "0.0.3",
            "OUTPUT_DIR": str(tmp_path / "out"),
            "ARTIFACTS_DIR": str(tmp_path / "artifacts"),
            "DRY_RUN": "1",
        },
        capture_output=True,
        text=True,
        check=True,
    )
    assert "worker-gateway_0.0.3_" in result.stdout
    assert ".tar.gz" in result.stdout


def test_scheduler_build_script_dry_run_reports_versioned_archive(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            "bash",
            str(ROOT / "scripts/build_a_scheduler_artifact.sh"),
        ],
        cwd=ROOT,
        env={
            "PATH": str(Path("/usr/bin")) + ":" + str(Path("/bin")) + ":" + str(Path("/usr/sbin")) + ":" + str(Path("/sbin")),
            "VERSION": "0.0.3",
            "OUTPUT_DIR": str(tmp_path / "out"),
            "ARTIFACTS_DIR": str(tmp_path / "artifacts"),
            "DRY_RUN": "1",
        },
        capture_output=True,
        text=True,
        check=True,
    )
    assert "a-scheduler_0.0.3_" in result.stdout
    assert ".tar.gz" in result.stdout


def test_record_artifact_script_writes_markdown_record(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / "artifacts"
    result = subprocess.run(
        [
            "bash",
            str(ROOT / "scripts/record_artifact.sh"),
            str(artifacts_dir),
            "worker-gateway",
            "0.0.3",
            "20260416_120000",
            "abc1234",
            "/tmp/out/worker-gateway_0.0.3_20260416_120000_abc1234.tar.gz",
            "docker build ...",
            "passed",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    record_path = Path(result.stdout.strip())
    assert record_path.exists()
    content = record_path.read_text(encoding="utf-8")
    assert "component: worker-gateway" in content
    assert "version: 0.0.3" in content
    assert "commit_sha: abc1234" in content
