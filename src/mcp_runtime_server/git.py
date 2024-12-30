"""Git operations."""
import logging
from pathlib import Path
from typing import Dict

from mcp_runtime_server.commands import run_command

logger = logging.getLogger(__name__)


async def clone_repository(url: str, target_dir: str, env_vars: Dict[str, str]) -> None:
    """Clone a GitHub repository using HTTPS.
    
    Args:
        url: Repository URL
        target_dir: Clone target directory
        env_vars: Environment variables for git
    """
    try:
        logger.debug(f"Original URL: {url}")
        
        # Ensure HTTPS URL
        if not url.startswith("https://"):
            if url.startswith("http://") or url.startswith("git@"):
                raise ValueError("Only HTTPS URLs are supported")
            url = f"https://{url}"
            
        logger.debug(f"Final URL: {url}")
        cmd = f"git clone {url} {target_dir}"
        logger.info(f"Executing git clone command: {cmd}")
        logger.debug(f"Clone target directory: {target_dir}")
        logger.debug(f"Clone working directory: {str(Path(target_dir).parent)}")
        logger.debug(f"Clone environment variables: {env_vars}")
            
        process = await run_command(
            cmd,
            str(Path(target_dir).parent),
            env_vars
        )
        stdout, stderr = await process.communicate()
        
        if stdout:
            logger.debug(f"Clone stdout: {stdout.decode()}")
        if stderr:
            logger.debug(f"Clone stderr: {stderr.decode()}")
            
        if process.returncode != 0:
            logger.error(f"Clone failed with return code {process.returncode}")
            raise RuntimeError(f"Failed to clone repository: {stderr.decode()}")
            
        logger.info("Repository cloned successfully")
            
    except Exception as e:
        logger.error(f"Clone failed: {str(e)}")
        raise RuntimeError(f"Clone failed: {str(e)}")
