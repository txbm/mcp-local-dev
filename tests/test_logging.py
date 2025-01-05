import logging
import json
from mcp_local_dev.logging import format_json_log, configure_logging, log_with_data

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
