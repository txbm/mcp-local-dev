"""Sandbox security restrictions."""
import os
import platform
import stat
from pathlib import Path
from typing import List, Optional
import resource

# Default resource limits
DEFAULT_LIMITS = {
    "AS": (resource.RLIMIT_AS, 1024 * 1024 * 1024),  # 1GB memory
    "CPU": (resource.RLIMIT_CPU, 60),  # 60 seconds CPU time
    "FSIZE": (resource.RLIMIT_FSIZE, 50 * 1024 * 1024),  # 50MB files
    "NOFILE": (resource.RLIMIT_NOFILE, 1024),  # 1024 open files
    "NPROC": (resource.RLIMIT_NPROC, 50),  # 50 processes
}

# Directories to bind mount from host system
BIND_MOUNTS = [
    "/usr",
    "/lib",
    "/lib64",
    "/bin",
    "/sbin"
]

# Paths that should never be accessible
BLOCKED_PATHS = [
    "/etc/shadow",
    "/etc/sudoers",
    "/.ssh",
    "/.aws",
    "/.config",
    "/root"
]


def apply_unix_permissions(path: Path) -> None:
    """Apply restrictive Unix permissions to a path.
    
    Args:
        path: Path to apply permissions to
    """
    # Owner read/write/execute only
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    
    # Apply recursively to all subdirectories
    if path.is_dir():
        for child in path.iterdir():
            apply_unix_permissions(child)


def apply_resource_limits() -> None:
    """Apply resource limits to the current process."""
    for name, (resource_type, limit) in DEFAULT_LIMITS.items():
        try:
            resource.setrlimit(resource_type, (limit, limit))
        except (ValueError, resource.error) as e:
            print(f"Warning: Failed to set {name} limit: {e}")


def setup_linux_namespaces() -> None:
    """Set up Linux namespaces for isolation."""
    try:
        import unshare
        
        # Create new mount namespace
        unshare.unshare(unshare.CLONE_NEWNS)
        
        # Make root mount private
        os.system("mount --make-rprivate /")
        
        # Create new PID namespace
        unshare.unshare(unshare.CLONE_NEWPID)
        
        # Create new network namespace (but keep loopback)
        unshare.unshare(unshare.CLONE_NEWNET)
        os.system("ip link set lo up")
        
    except ImportError:
        print("Warning: python-unshare not available, namespace isolation disabled")
    except Exception as e:
        print(f"Warning: Failed to set up namespaces: {e}")


def mount_sandbox_bindings(root: Path) -> None:
    """Set up sandbox mount bindings.
    
    Args:
        root: Sandbox root directory
    """
    try:
        # Mount temporary filesystem for /tmp
        os.system(f"mount -t tmpfs none {root}/tmp")
        
        # Bind mount necessary system directories read-only
        for src in BIND_MOUNTS:
            if Path(src).exists():
                dst = root / src.lstrip('/')
                dst.parent.mkdir(parents=True, exist_ok=True)
                os.system(f"mount --bind {src} {dst}")
                os.system(f"mount -o remount,ro,bind {dst}")
                
    except Exception as e:
        print(f"Warning: Failed to set up mount bindings: {e}")


def block_dangerous_paths() -> None:
    """Block access to sensitive paths."""
    for path in BLOCKED_PATHS:
        if Path(path).exists():
            try:
                # Remove all permissions
                os.chmod(path, 0)
            except Exception as e:
                print(f"Warning: Failed to block {path}: {e}")


def setup_seccomp() -> None:
    """Set up seccomp syscall filtering."""
    try:
        from seccomp import SyscallFilter, ALLOW, KILL
        
        # Create whitelist filter
        f = SyscallFilter(KILL)
        
        # Allow basic process operations
        f.add_rule(ALLOW, "read")
        f.add_rule(ALLOW, "write")
        f.add_rule(ALLOW, "open")
        f.add_rule(ALLOW, "close")
        f.add_rule(ALLOW, "stat")
        f.add_rule(ALLOW, "fstat")
        f.add_rule(ALLOW, "lstat")
        f.add_rule(ALLOW, "poll")
        f.add_rule(ALLOW, "lseek")
        f.add_rule(ALLOW, "mmap")
        f.add_rule(ALLOW, "mprotect")
        f.add_rule(ALLOW, "munmap")
        f.add_rule(ALLOW, "brk")
        f.add_rule(ALLOW, "rt_sigaction")
        f.add_rule(ALLOW, "rt_sigprocmask")
        f.add_rule(ALLOW, "rt_sigreturn")
        f.add_rule(ALLOW, "ioctl")
        f.add_rule(ALLOW, "pread64")
        f.add_rule(ALLOW, "pwrite64")
        f.add_rule(ALLOW, "readv")
        f.add_rule(ALLOW, "writev")
        f.add_rule(ALLOW, "access")
        f.add_rule(ALLOW, "pipe")
        f.add_rule(ALLOW, "select")
        f.add_rule(ALLOW, "sched_yield")
        f.add_rule(ALLOW, "mremap")
        f.add_rule(ALLOW, "msync")
        f.add_rule(ALLOW, "mincore")
        f.add_rule(ALLOW, "madvise")
        f.add_rule(ALLOW, "pause")
        f.add_rule(ALLOW, "nanosleep")
        f.add_rule(ALLOW, "getitimer")
        f.add_rule(ALLOW, "alarm")
        f.add_rule(ALLOW, "setitimer")
        f.add_rule(ALLOW, "getpid")
        f.add_rule(ALLOW, "sendfile")
        f.add_rule(ALLOW, "socket")
        f.add_rule(ALLOW, "connect")
        f.add_rule(ALLOW, "accept")
        f.add_rule(ALLOW, "sendto")
        f.add_rule(ALLOW, "recvfrom")
        f.add_rule(ALLOW, "sendmsg")
        f.add_rule(ALLOW, "recvmsg")
        f.add_rule(ALLOW, "shutdown")
        f.add_rule(ALLOW, "bind")
        f.add_rule(ALLOW, "listen")
        f.add_rule(ALLOW, "getsockname")
        f.add_rule(ALLOW, "getpeername")
        f.add_rule(ALLOW, "socketpair")
        f.add_rule(ALLOW, "setsockopt")
        f.add_rule(ALLOW, "getsockopt")
        f.add_rule(ALLOW, "clone")
        f.add_rule(ALLOW, "fork")
        f.add_rule(ALLOW, "vfork")
        f.add_rule(ALLOW, "execve")
        f.add_rule(ALLOW, "exit")
        f.add_rule(ALLOW, "wait4")
        f.add_rule(ALLOW, "kill")
        f.add_rule(ALLOW, "uname")
        f.add_rule(ALLOW, "fcntl")
        f.add_rule(ALLOW, "flock")
        f.add_rule(ALLOW, "fsync")
        f.add_rule(ALLOW, "fdatasync")
        f.add_rule(ALLOW, "truncate")
        f.add_rule(ALLOW, "ftruncate")
        f.add_rule(ALLOW, "getcwd")
        f.add_rule(ALLOW, "chdir")
        f.add_rule(ALLOW, "fchdir")
        f.add_rule(ALLOW, "rename")
        f.add_rule(ALLOW, "mkdir")
        f.add_rule(ALLOW, "rmdir")
        f.add_rule(ALLOW, "creat")
        f.add_rule(ALLOW, "link")
        f.add_rule(ALLOW, "unlink")
        f.add_rule(ALLOW, "symlink")
        f.add_rule(ALLOW, "readlink")
        f.add_rule(ALLOW, "chmod")
        f.add_rule(ALLOW, "fchmod")
        f.add_rule(ALLOW, "chown")
        f.add_rule(ALLOW, "fchown")
        f.add_rule(ALLOW, "lchown")
        f.add_rule(ALLOW, "umask")
        
        # Load the filter
        f.load()
        
    except ImportError:
        print("Warning: python-seccomp not available, syscall filtering disabled")
    except Exception as e:
        print(f"Warning: Failed to set up seccomp filtering: {e}")


def apply_restrictions(root: Path) -> None:
    """Apply security restrictions for a sandbox.
    
    Args:
        root: Sandbox root directory
    """
    # Basic Unix permissions
    apply_unix_permissions(root)
    
    # Resource limits
    apply_resource_limits()
    
    # Platform specific restrictions
    system = platform.system()
    
    if system == "Linux":
        setup_linux_namespaces()
        mount_sandbox_bindings(root)
        setup_seccomp()
        
    block_dangerous_paths()


def remove_restrictions(root: Path) -> None:
    """Remove security restrictions from a sandbox.
    
    Args:
        root: Sandbox root directory
    """
    try:
        # Unmount any remaining mounts
        os.system(f"umount -R {root} 2>/dev/null")
        
        # Reset permissions to normal
        os.chmod(root, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
        
    except Exception as e:
        print(f"Warning: Failed to remove restrictions: {e}")
