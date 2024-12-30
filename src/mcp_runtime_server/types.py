"""Runtime server type definitions."""
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


RuntimeManager = Enum('RuntimeManager', [
    ('NODE', 'node'),
    ('BUN', 'bun'),
    ('UV', 'uv')
])


RunResult = Enum('RunResult', [
    'PASS',
    'FAIL',
    'ERROR',
    'TIMEOUT'
])


CaptureMode = Enum('CaptureMode', [
    'FULL',
    'STDOUT_ONLY',
    'STDERR_ONLY',
    'NONE'
])


@dataclass(frozen=True)
class RuntimeConfig:
    """Configuration for runtime environments."""
    manager: RuntimeManager
    github_url: str


@dataclass(frozen=True)
class Environment:
    """Runtime environment state."""
    id: str
    config: RuntimeConfig
    created_at: datetime
    working_dir: str


@dataclass(frozen=True)
class TestConfig:
    """Test configuration."""
    name: str
    command: str
    timeout_seconds: int = 30
    expected_exit_code: int = 0
    expected_output: Optional[str] = None


@dataclass(frozen=True)
class CaptureConfig:
    """Output capture configuration."""
    mode: CaptureMode = CaptureMode.FULL
    max_size: int = 1024 * 1024  # 1MB default


@dataclass(frozen=True)
class CapturedOutput:
    """Captured process output."""
    stdout: str
    stderr: str
    exit_code: int
    start_time: datetime
    end_time: datetime


@dataclass(frozen=True)
class TestRun:
    """Test execution results."""
    config: TestConfig
    result: RunResult
    captured: CapturedOutput
    error_message: Optional[str] = None
    failure_details: Optional[Dict[str, Any]] = None