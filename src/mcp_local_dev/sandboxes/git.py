"""Functions for working with Git and Github"""

from typing import Optional
from pathlib import Path


from mcp_local_dev.types import Sandbox
from mcp_local_dev.logging import get_logger
from mcp_local_dev.sandboxes.sandbox import run_sandboxed_command


def normalize_github_url(url: str) -> str:
    """Convert GitHub URL to HTTPS format."""
    if not url:
        raise ValueError("URL cannot be empty")

    if "?" in url or "#" in url:
        raise ValueError("URLs with query parameters or fragments not supported")

    if url.startswith("git@github.com:"):
        return f"https://github.com/{url.split(':')[1]}"

    if not url.startswith(("http://", "https://", "github.com")):
        return f"https://github.com/{url}"

    if url.startswith("http://"):
        raise ValueError("HTTP URLs not supported, use HTTPS")

    if url.startswith("github.com"):
        return f"https://{url}"

    return url


logger = get_logger(__name__)


async def clone_github_repository(
    sandbox: Sandbox, url: str, branch: Optional[str], subdir: Optional[str] = None
) -> Path:
    if not url:
        raise ValueError("URL cannot be empty")

    target_dir = sandbox.work_dir

    logger.debug(
        {"event": "clone_github_repository", "url": url, "target_dir": str(target_dir)}
    )

    url = normalize_github_url(url)

    cmd = f"git clone {url} {target_dir}"
    if branch:
        cmd += f" -b {branch}"

    logger.debug(
        {
            "event": "cloning_repository",
            "command": cmd,
            "target_dir": str(target_dir),
            "parent_dir": str(Path(target_dir).parent),
        }
    )

    returncode, stdout, stderr = await run_sandboxed_command(sandbox, cmd)
    if returncode != 0:
        logger.error(
            {
                "event": "clone_failed",
                "return_code": returncode,
                "stderr": stderr.decode(),
            }
        )
        raise RuntimeError(f"Failed to clone repository: {stderr.decode()}")

    logger.info(
        {"event": "repository_cloned", "url": url, "target_dir": str(target_dir)}
    )

    return target_dir
