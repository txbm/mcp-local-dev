"""Integration tests for sandbox functionality."""
import os
import platform
import pytest
import tempfile
from pathlib import Path
import psutil

from mcp_runtime_server.sandbox.environment import create_sandbox, cleanup_sandbox
from mcp_runtime_server.sandbox.security import DEFAULT_LIMITS
from mcp_runtime_server.binaries.fetcher import ensure_binary


@pytest.mark.asyncio
async def test_sandbox_isolation():
    """Test that sandbox environments are properly isolated."""
    sandbox = create_sandbox()
    try:
        # Verify directory structure
        assert sandbox.root.exists()
        assert (sandbox.root / "bin").exists()
        assert (sandbox.root / "tmp").exists()
        assert (sandbox.root / "home").exists()
        
        # Verify environment variables
        assert sandbox.env_vars["HOME"].startswith(str(sandbox.root))
        assert sandbox.env_vars["TMPDIR"].startswith(str(sandbox.root))
        
        # Test file isolation
        test_file = sandbox.root / "test.txt"
        with open(test_file, "w") as f:
            f.write("test")
            
        # Verify permissions
        stat = test_file.stat()
        assert stat.st_mode & 0o777 == 0o600  # Only owner read/write
        
        # Verify process isolation (Linux only)
        if platform.system() == "Linux":
            # Try to access outside sandbox
            blocked = Path("/etc/shadow")
            if blocked.exists():
                with pytest.raises(PermissionError):
                    blocked.read_text()
                    
    finally:
        cleanup_sandbox(sandbox)
        assert not sandbox.root.exists()


@pytest.mark.asyncio
async def test_resource_limits():
    """Test that resource limits are enforced."""
    sandbox = create_sandbox()
    try:
        # Test memory limit
        mem_limit = DEFAULT_LIMITS["AS"][1]
        
        # Try to allocate more than limit
        code = f"""
        x = bytearray({mem_limit * 2})
        """
        
        with tempfile.NamedTemporaryFile(suffix=".py") as tf:
            tf.write(code.encode())
            tf.flush()
            
            proc = psutil.Popen(
                ["python", tf.name],
                env=sandbox.env_vars,
                cwd=str(sandbox.root)
            )
            
            # Process should be killed by resource limits
            proc.wait(timeout=5)
            assert proc.returncode != 0
            
        # Test file size limit
        size_limit = DEFAULT_LIMITS["FSIZE"][1]
        test_file = sandbox.root / "big_file"
        
        with pytest.raises(OSError):
            with open(test_file, "wb") as f:
                f.write(b"0" * (size_limit + 1))
                
    finally:
        cleanup_sandbox(sandbox)


@pytest.mark.asyncio
async def test_binary_installation():
    """Test installing and running binaries in sandbox."""
    sandbox = create_sandbox()
    try:
        # Get Node.js binary
        node_path = await ensure_binary("node")
        
        # Copy to sandbox bin directory
        dest = sandbox.bin_dir / "node"
        dest.write_bytes(node_path.read_bytes())
        dest.chmod(0o755)
        
        # Test running Node
        code = "console.log('hello from sandbox')"
        proc = psutil.Popen(
            ["node", "-e", code],
            env=sandbox.env_vars,
            cwd=str(sandbox.root),
            stdout=psutil.subprocess.PIPE,
            stderr=psutil.subprocess.PIPE
        )
        
        stdout, stderr = proc.communicate()
        assert proc.returncode == 0
        assert b"hello from sandbox" in stdout
        
    finally:
        cleanup_sandbox(sandbox)


@pytest.mark.asyncio
async def test_process_isolation():
    """Test that processes are properly isolated."""
    sandbox = create_sandbox()
    try:
        if platform.system() == "Linux":
            # Try to fork bomb
            code = """
            import os
            while True:
                os.fork()
            """
            
            with tempfile.NamedTemporaryFile(suffix=".py") as tf:
                tf.write(code.encode())
                tf.flush()
                
                proc = psutil.Popen(
                    ["python", tf.name],
                    env=sandbox.env_vars,
                    cwd=str(sandbox.root)
                )
                
                # Process should be killed by NPROC limit
                proc.wait(timeout=5)
                assert proc.returncode != 0
                
            # Verify process tree is cleaned up
            children = psutil.Process().children(recursive=True)
            assert not any(
                p.cwd().startswith(str(sandbox.root))
                for p in children
            )
            
    finally:
        cleanup_sandbox(sandbox)


@pytest.mark.asyncio
async def test_network_isolation():
    """Test network isolation."""
    sandbox = create_sandbox()
    try:
        if platform.system() == "Linux":
            # Try to bind to privileged port
            code = """
            import socket
            s = socket.socket()
            s.bind(('127.0.0.1', 80))
            """
            
            with tempfile.NamedTemporaryFile(suffix=".py") as tf:
                tf.write(code.encode())
                tf.flush()
                
                proc = psutil.Popen(
                    ["python", tf.name],
                    env=sandbox.env_vars,
                    cwd=str(sandbox.root)
                )
                
                # Should fail due to network namespace
                proc.wait(timeout=5)
                assert proc.returncode != 0
                
        # Verify loopback is working
        code = """
        import socket
        s = socket.socket()
        s.bind(('127.0.0.1', 12345))
        """
        
        with tempfile.NamedTemporaryFile(suffix=".py") as tf:
            tf.write(code.encode())
            tf.flush()
            
            proc = psutil.Popen(
                ["python", tf.name],
                env=sandbox.env_vars,
                cwd=str(sandbox.root)
            )
            
            # Should succeed
            proc.wait(timeout=5)
            assert proc.returncode == 0
            
    finally:
        cleanup_sandbox(sandbox)


@pytest.mark.asyncio
async def test_filesystem_isolation():
    """Test filesystem isolation."""
    sandbox = create_sandbox()
    try:
        # Write file in sandbox
        test_file = sandbox.root / "test.txt"
        test_content = "hello sandbox"
        test_file.write_text(test_content)
        
        # Try to read it from Python
        code = f"""
        with open('test.txt') as f:
            content = f.read()
            assert content == '{test_content}'
            
        # Try to write outside sandbox
        try:
            with open('/etc/passwd', 'a') as f:
                f.write('test')
            assert False, "Should not be able to write outside sandbox"
        except PermissionError:
            pass
        """
        
        with tempfile.NamedTemporaryFile(suffix=".py") as tf:
            tf.write(code.encode())
            tf.flush()
            
            proc = psutil.Popen(
                ["python", tf.name],
                env=sandbox.env_vars,
                cwd=str(sandbox.root)
            )
            
            proc.wait(timeout=5)
            assert proc.returncode == 0
            
    finally:
        cleanup_sandbox(sandbox)