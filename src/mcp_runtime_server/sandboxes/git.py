from typing import Optional
from pathlib import Path


from mcp_runtime_server.types import Sandbox
from mcp_runtime_server.logging import get_logger
from mcp_runtime_server.sandboxes.sandbox import run_sandboxed_command

logger = get_logger(__name__)


async def clone_github_repository(
    sandbox: Sandbox, 
    url: str, 
    branch: Optional[str], 
    subdir: Optional[str] = None
) -> Path:
    target_dir = sandbox.work_dir

    logger.debug(
        {"event": "clone_github_repository", "url": url, "target_dir": str(target_dir)}
    )

    # Normalize GitHub URL to HTTPS format
    if url.startswith("git@github.com:"):
        url = f"https://github.com/{url.split(':', 1)[1]}"
    elif url.startswith("http://"):
        raise ValueError("HTTP URLs are not supported, use HTTPS")
    elif not url.startswith("https://"):
        # Handle shorthand formats like "owner/repo"
        if "/" in url and not url.startswith("github.com"):
            url = f"https://github.com/{url}"
        else:
            url = f"https://{url}"
    
    if not url.startswith("https://github.com"):
        raise ValueError("Only GitHub repositories are supported")

    logger.debug({"event": "clone_url_processed", "final_url": url})

    # Build command
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

    process = await run_sandboxed_command(sandbox, cmd)
    stdout, stderr = await process.communicate()

    if stdout:
        logger.debug({"event": "clone_stdout", "output": stdout.decode()})
    if stderr:
        logger.debug({"event": "clone_stderr", "output": stderr.decode()})

    if process.returncode != 0:
        logger.error(
            {
                "event": "clone_failed",
                "return_code": process.returncode,
                "stderr": stderr.decode(),
            }
        )
        raise RuntimeError(f"Failed to clone repository: {stderr.decode()}")

    logger.info(
        {"event": "repository_cloned", "url": url, "target_dir": str(target_dir)}
    )

    return target_dir
