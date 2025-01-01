"""Type definitions for the MCP Runtime Server."""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional, List

@dataclass
class Environment:
    """Runtime environment configuration."""
    work_dir: str
    bin_dir: str
    env_vars: Dict[str, str]

@dataclass
class TestCase:
    """Test case execution result."""
    name: str
    status: str
    output: List[str]
    failure_message: Optional[str] = None
    duration: Optional[float] = None

@dataclass
class RunTestResult:
    """Results from a test framework run."""
    success: bool
    framework: str
    passed: Optional[int] = None
    failed: Optional[int] = None
    skipped: Optional[int] = None
    total: Optional[int] = None
    failures: List[Dict[str, Any]] = None
    warnings: List[str] = None
    test_cases: List[Dict[str, Any]] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    error: Optional[str] = None

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.failures is None:
            self.failures = []
        if self.warnings is None:
            self.warnings = []
        if self.test_cases is None:
            self.test_cases = []
