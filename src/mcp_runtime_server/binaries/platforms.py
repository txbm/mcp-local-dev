"""Platform detection and mapping."""
import platform
import sys
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class PlatformInfo:
    """Platform information."""
    os_name: str
    arch: str
    format: str
    node_platform: str
    bun_platform: str
    uv_platform: str


# Architecture mappings
ARCH_MAPPINGS = {
    "x86_64": {
        "node": "x64",
        "bun": "x64",
        "uv": "x86_64"
    },
    "aarch64": {
        "node": "arm64",
        "bun": "aarch64",
        "uv": "aarch64"
    },
    "arm64": {
        "node": "arm64",
        "bun": "aarch64",
        "uv": "aarch64"
    }
}

# Platform mappings
PLATFORM_MAPPINGS = {
    "Linux": {
        "node": "linux",
        "bun": "linux",
        "uv": "unknown-linux-gnu",  # UV uses gnu suffix for Linux
        "format": "tar.gz"
    },
    "Darwin": {
        "node": "darwin",
        "bun": "darwin",
        "uv": "apple-darwin",  # UV uses apple prefix for macOS
        "format": "tar.gz"
    },
    "Windows": {
        "node": "win",
        "bun": "windows",
        "uv": "pc-windows-msvc",  # UV uses MSVC suffix for Windows
        "format": "zip"
    }
}


def get_platform_info() -> PlatformInfo:
    """Get current platform information.
    
    Returns:
        PlatformInfo with platform details
        
    Raises:
        RuntimeError: If platform is not supported
    """
    system = platform.system()
    machine = platform.machine().lower()
    
    if system not in PLATFORM_MAPPINGS:
        raise RuntimeError(f"Unsupported operating system: {system}")
        
    # Handle ARM64 naming variations
    if machine in ("arm64", "aarch64"):
        machine = "aarch64"
        
    if machine not in ARCH_MAPPINGS:
        raise RuntimeError(f"Unsupported architecture: {machine}")
        
    platform_map = PLATFORM_MAPPINGS[system]
    arch_map = ARCH_MAPPINGS[machine]
    
    # UV uniquely combines arch and platform
    # e.g., aarch64-apple-darwin, x86_64-unknown-linux-gnu
    # And uses this full string in the release archive name
    if system == "Linux":
        uv_platform = f"{arch_map['uv']}-{platform_map['uv']}"
    else:  # Darwin, Windows
        uv_platform = f"{arch_map['uv']}-{platform_map['uv']}"
    
    return PlatformInfo(
        os_name=system.lower(),
        arch=machine,
        format=platform_map["format"],
        node_platform=f"{platform_map['node']}-{arch_map['node']}",
        bun_platform=f"{platform_map['bun']}-{arch_map['bun']}",
        uv_platform=uv_platform
    )


def is_platform_supported() -> bool:
    """Check if current platform is supported.
    
    Returns:
        True if platform is supported
    """
    try:
        get_platform_info()
        return True
    except RuntimeError:
        return False