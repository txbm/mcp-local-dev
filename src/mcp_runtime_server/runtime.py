"""Runtime environment management functions."""
import asyncio
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
import psutil
from typing import Dict, Optional, Tuple, AsyncGenerator

from .types import (
    RuntimeConfig,
    RuntimeEnv,
    CapturedOutput,
    ProcessStats,
    CaptureConfig,
    CaptureMode
)

# Global storage for active environments
ACTIVE_ENVS: Dict[str, RuntimeEnv] = {}

async def create_environment(config: RuntimeConfig) -> RuntimeEnv:
    """Create a new runtime environment.
    
    Args:
        config: Runtime configuration
        
    Returns:
        RuntimeEnv with environment details
        
    Raises:
        RuntimeError: If environment creation fails
    """
    env_id = str(uuid.uuid4())
    
    # Create working directory
    work_dir = (config.working_dir if config.working_dir 
                else tempfile.mkdtemp(prefix=f"mcp-runtime-{env_id}-"))
    
    # Prepare environment variables
    env_vars = os.environ.copy()
    env_vars.update(config.env)
    
    env = RuntimeEnv(
        id=env_id,
        config=config,
        created_at=datetime.utcnow(),
        working_dir=work_dir,
        env_vars=env_vars
    )
    
    ACTIVE_ENVS[env_id] = env
    return env


async def cleanup_environment(env_id: str, force: bool = False) -> None:
    """Clean up a runtime environment.
    
    Args:
        env_id: Environment identifier
        force: Force cleanup even if processes are running
        
    Raises:
        RuntimeError: If cleanup fails
    """
    if env_id not in ACTIVE_ENVS:
        return
        
    env = ACTIVE_ENVS[env_id]
    
    # Kill any running processes
    if force:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if env.working_dir in proc.cmdline():
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    
    # Clean up working directory if it was temporary
    if not env.config.working_dir:
        Path(env.working_dir).unlink(missing_ok=True)
    
    del ACTIVE_ENVS[env_id]


async def monitor_process(
    process: asyncio.subprocess.Process,
    limits: Optional[ResourceLimits] = None
) -> AsyncGenerator[ProcessStats, None]:
    """Monitor a running process and yield statistics.
    
    Args:
        process: Process to monitor
        limits: Optional resource limits
        
    Yields:
        ProcessStats with current process statistics
    """
    start_time = datetime.utcnow()
    peak_memory = 0.0
    peak_cpu = 0.0
    cpu_samples = []
    
    try:
        while process.returncode is None:
            try:
                proc = psutil.Process(process.pid)
                memory = proc.memory_info().rss / 1024 / 1024  # Convert to MB
                cpu = proc.cpu_percent()
                
                peak_memory = max(peak_memory, memory)
                peak_cpu = max(peak_cpu, cpu)
                cpu_samples.append(cpu)
                
                stats = ProcessStats(
                    peak_memory_mb=peak_memory,
                    avg_cpu_percent=sum(cpu_samples) / len(cpu_samples),
                    duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                    peak_cpu_percent=peak_cpu
                )
                
                # Check resource limits
                if limits:
                    if (limits.max_memory_mb and 
                        memory > limits.max_memory_mb):
                        process.kill()
                        break
                    if (limits.max_cpu_percent and 
                        stats.avg_cpu_percent > limits.max_cpu_percent):
                        process.kill()
                        break
                
                yield stats
                await asyncio.sleep(0.1)  # Don't overwhelm the system
                
            except psutil.NoSuchProcess:
                break
                
    finally:
        if process.returncode is None:
            process.kill()


async def run_in_env(
    env_id: str,
    command: str,
    capture_config: CaptureConfig
) -> CapturedOutput:
    """Run a command in a runtime environment.
    
    Args:
        env_id: Environment identifier
        command: Command to run
        capture_config: Output capture configuration
        
    Returns:
        CapturedOutput with process results
        
    Raises:
        RuntimeError: If command execution fails
    """
    if env_id not in ACTIVE_ENVS:
        raise RuntimeError(f"Environment {env_id} not found")
        
    env = ACTIVE_ENVS[env_id]
    start_time = datetime.utcnow()
    
    # Prepare stdout/stderr handling
    stdout = asyncio.subprocess.PIPE if capture_config.mode in (
        CaptureMode.STDOUT, CaptureMode.BOTH) else None
    stderr = asyncio.subprocess.PIPE if capture_config.mode in (
        CaptureMode.STDERR, CaptureMode.BOTH) else None
    
    # Start process
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=stdout,
        stderr=stderr,
        cwd=env.working_dir,
        env=env.env_vars
    )
    
    # Capture output and monitor resources
    output, error = await process.communicate()
    stats = None
    
    if capture_config.include_stats:
        stats_gen = monitor_process(process, env.config.resource_limits)
        async for current_stats in stats_gen:
            stats = current_stats
    
    end_time = datetime.utcnow()
    
    # Truncate output if needed
    if capture_config.max_output_size:
        output = output[:capture_config.max_output_size] if output else b""
        error = error[:capture_config.max_output_size] if error else b""
    
    return CapturedOutput(
        stdout=output.decode() if output else "",
        stderr=error.decode() if error else "",
        exit_code=process.returncode or 0,
        start_time=start_time,
        end_time=end_time,
        stats=stats
    )