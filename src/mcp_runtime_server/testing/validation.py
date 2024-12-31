"""Response validation."""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, RootModel

class TextContent(BaseModel):
    type: str = "text"
    text: str

class Tool(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]

class RunTestResult(BaseModel):
    success: bool
    framework: str
    passed: Optional[int] = None
    failed: Optional[int] = None
    skipped: Optional[int] = None
    total: Optional[int] = None
    failures: List[Dict[str, Any]] = []
    warnings: List[str] = []
    test_cases: List[Dict[str, Any]] = []
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    error: Optional[str] = None