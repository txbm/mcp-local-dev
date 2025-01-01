"""Core type definitions."""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict

class Runtime(str, Enum):
    """Runtime environment types."""
    PYTHON = "python"
    NODE = "node"
    BUN = "bun"

class PackageManager(str, Enum):
    """Package manager types."""
    UV = "uv"  # Python
    NPM = "npm"  # Node.js
    BUN = "bun"  # Bun
    
    @classmethod
    def for_runtime(cls, runtime: Runtime) -> "PackageManager":
        """Get default package manager for runtime."""
        if runtime == Runtime.PYTHON:
            return cls.UV
        elif runtime == Runtime.NODE:
            return cls.NPM
        elif runtime == Runtime.BUN:
            return cls.BUN
        raise ValueError(f"No package manager for runtime: {runtime}")

@dataclass(frozen=True)
class Environment:
    """Runtime environment instance."""
    id: str
    runtime: Runtime
    work_dir: Path  
    created_at: datetime
    env_vars: Dict[str, str]