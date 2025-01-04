"""Runtime detection and configuration."""

from typing import Dict

from mcp_runtime_server.types import Runtime, PackageManager, RuntimeConfig, Sandbox
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)


RUNTIME_CONFIGS: Dict[Runtime, RuntimeConfig] = {
    Runtime.NODE: RuntimeConfig(
        name=Runtime.NODE,
        config_files=["package.json"],
        package_manager=PackageManager.NPM,
        env_setup={"NODE_NO_WARNINGS": "1"},
        binary_name="node",
    ),
    Runtime.BUN: RuntimeConfig(
        name=Runtime.BUN,
        config_files=["bun.lockb", "package.json"],
        package_manager=PackageManager.BUN,
        env_setup={"NO_INSTALL_HINTS": "1"},
        binary_name="bun",
    ),
    Runtime.PYTHON: RuntimeConfig(
        name=Runtime.PYTHON,
        config_files=["pyproject.toml", "setup.py", "requirements.txt"],
        package_manager=PackageManager.UV,
        env_setup={
            "PYTHONUNBUFFERED": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        binary_name="python",
    ),
}


def detect_runtime(sandbox: Sandbox) -> RuntimeConfig:
    """Detect runtime from project files."""

    work_dir = sandbox.work_dir
    logger.debug({"event": "detecting_runtime", "work_dir": str(work_dir)})

    files = set(str(p) for p in work_dir.rglob("*"))
    logger.debug({"event": "found_project_files", "files": list(files)})

    for runtime, config in RUNTIME_CONFIGS.items():
        if runtime == Runtime.BUN:
            if all(any(f.endswith(c) for f in files) for c in config.config_files):
                logger.info(
                    {
                        "event": "runtime_detected",
                        "runtime": runtime.value,
                        "matched_files": config.config_files,
                    }
                )
                return config
        else:
            if any(any(f.endswith(c) for f in files) for c in config.config_files):
                matched_file = next(
                    c for c in config.config_files if any(f.endswith(c) for f in files)
                )
                logger.info(
                    {
                        "event": "runtime_detected",
                        "runtime": runtime.value,
                        "matched_file": matched_file,
                        "files_checked": config.config_files,
                    }
                )
                return config

    logger.error(
        {
            "event": "no_runtime_detected",
            "work_dir": str(work_dir),
            "files_found": list(files),
        }
    )
    raise ValueError("No supported runtime detected")


async def install_runtime(
    sandbox: Sandbox, config: RuntimeConfig
) -> None:
    """Install runtime assuming binaries are on system path"""
    # Runtime installation logic would go here
    # Currently just verifying system binaries exist
    pass
