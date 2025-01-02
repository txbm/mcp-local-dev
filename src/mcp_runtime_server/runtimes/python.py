from pathlib import Path

from mcp_runtime_server.utils.github import fetch_latest_release_version
from mcp_runtime_server.runtimes.platforms import get_platform_info
from mcp_runtime_server.sandboxes.sandbox import (
    run_sandboxed_command,
)
from mcp_runtime_server.sandboxes.cache import (
    get_binary_path,
    cache_binary,
    cleanup_cache,
)
from mcp_runtime_server.types import PlatformInfo, RuntimeConfig, Sandbox
from mcp_runtime_server.logging import get_logger
from mcp_runtime_server.utils.fetching import (
    download_url,
    download_checksum,
    extract_archive,
)

logger = get_logger(__name__)


async def _fetch_latest_uv(
    sandbox: Sandbox, config: RuntimeConfig, platform_info: PlatformInfo
):

    owner = "astral-sh"
    repo = "uv"
    version = await fetch_latest_release_version(owner, repo)
    cached = get_binary_path(config.binary_name, version)

    if not cached:
        url_vars = {
            "version": version,
            "version_prefix": config.version_prefix,
            "platform": platform_info.uv_platform,
            "format": platform_info.format,
            "arch": platform_info.arch,
            "owner": owner,
            "repo": repo,
        }
        archive_url = config.url_template.format(**url_vars)
        checksum_url = config.checksum_template.format(**url_vars)
        tmp_dir = sandbox.tmp_dir
        archive_path = tmp_dir / Path(archive_url).name

        logger.debug(
            {
                "event": "downloading_runtime_binary",
                "runtime": config.name.value,
                "url": download_url,
                "destination": archive_path,
            }
        )

        await download_url(archive_url, archive_path)
        checksum = await download_checksum(checksum_url, archive_path)
        cached = cache_binary(config.binary_name, version, archive_path, checksum)
        cleanup_cache()

    return extract_archive(cached, sandbox.bin_dir)


async def install_runtime(
    sandbox: Sandbox, config: RuntimeConfig
) -> tuple[Path, Path, Path]:

    platform_info = get_platform_info()

    await _fetch_latest_uv(sandbox, config, platform_info)

    process = await run_sandboxed_command(sandbox, "uv sync --all-extras")
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(
            f"Python runtime install failed {process.returncode}\n"
            f"stdout: {stdout.decode()}\n"
            f"stderr: {stderr.decode()}"
        )

    return (
        sandbox.bin_dir / "python",
        sandbox.bin_dir / "uv",
        sandbox.bin_dir / "pytest",
    )
