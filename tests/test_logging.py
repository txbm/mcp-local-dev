import logging
import json
import pytest
from mcp_local_dev.logging import format_json_log, configure_logging, log_with_data, get_logger

def test_format_json_log():
    """Test JSON log formatting"""
    record = logging.LogRecord(
        "test", logging.INFO, "test.py", 10, 
        "Test message", (), None
    )
    record.asctime = "2024-01-01 00:00:00"
    
    output = format_json_log(record)
    data = json.loads(output.strip("\033[32m\033[0m"))  # Remove color codes
    
    assert data["level"] == "INFO"
    assert data["msg"] == "Test message"
    assert data["ts"] == "2024-01-01 00:00:00"

@pytest.mark.parametrize("level,expected_color", [
    (logging.DEBUG, "\033[34m"),    # BLUE
    (logging.INFO, "\033[32m"),     # GREEN
    (logging.WARNING, "\033[33m"),  # YELLOW
    (logging.ERROR, "\033[31m\033[1m"),  # RED+BOLD
    (logging.CRITICAL, "\033[35m\033[1m")  # MAGENTA+BOLD
])
def test_format_json_log_colors(level, expected_color):
    """Test log level color coding"""
    record = logging.LogRecord(
        "test", level, "test.py", 10, 
        "Test message", (), None
    )
    record.asctime = "2024-01-01 00:00:00"
    
    output = format_json_log(record)
    assert output.startswith(expected_color)
    assert output.endswith("\033[0m")

def test_log_with_data():
    """Test structured logging with data"""
    logger = logging.getLogger("test")
    logger.setLevel(logging.INFO)
    
    test_data = {"key": "value"}
    log_with_data(logger, logging.INFO, "Test message", test_data)
    
    # Verify through handler
    class TestHandler(logging.Handler):
        def __init__(self):
            super().__init__()
            self.records = []
            
        def emit(self, record):
            self.records.append(record)
            
    handler = TestHandler()
    logger.addHandler(handler)
    
    log_with_data(logger, logging.INFO, "Test message", test_data)
    assert len(handler.records) == 1
    assert handler.records[0].data == test_data

def test_log_with_data_json_structure():
    """Test structured logging produces valid JSON"""
    logger = logging.getLogger("test")
    
    # Use StringIO to capture output
    from io import StringIO
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    
    test_data = {"key": "value", "nested": {"foo": "bar"}}
    log_with_data(logger, logging.INFO, "Test message", test_data)
    
    # Verify JSON can be parsed and has expected structure
    output = stream.getvalue()
    data = json.loads(output.strip("\033[32m\033[0m"))  # Remove color codes
    assert "ts" in data
    assert data["level"] == "INFO" 
    assert data["msg"] == "Test message"
    assert data["data"] == test_data

def test_get_logger():
    """Test logger retrieval"""
    logger = get_logger("test_module")
    assert logger.name == "mcp_runtime_server.test_module"
    
def test_configure_logging():
    """Test logging configuration"""
    configure_logging()
    logger = logging.getLogger("mcp_local_dev")
    
    assert logger.level == logging.INFO
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], logging.StreamHandler)
    assert not logger.propagate
