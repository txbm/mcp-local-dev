import logging
import json
import pytest
from mcp_local_dev.logging import (
    JsonFormatter,
    configure_logging,
    log_with_data,
    get_logger,
)


def test_format_json_log():
    """Test JSON log formatting"""
    formatter = JsonFormatter()
    record = logging.LogRecord(
        "test", logging.INFO, "test.py", 10, "Test message", (), None
    )

    output = formatter.format(record)
    data = json.loads(output.strip("\033[32m\033[0m"))  # Remove color codes

    assert data["level"] == "INFO"
    assert data["msg"] == "Test message"


@pytest.mark.parametrize(
    "level,expected_color",
    [
        (logging.DEBUG, "\033[34m"),  # BLUE
        (logging.INFO, "\033[32m"),  # GREEN
        (logging.WARNING, "\033[33m"),  # YELLOW
        (logging.ERROR, "\033[31m\033[1m"),  # RED+BOLD
        (logging.CRITICAL, "\033[35m\033[1m"),  # MAGENTA+BOLD
    ],
)
def test_format_json_log_colors(level, expected_color):
    """Test log level color coding"""
    formatter = JsonFormatter()
    record = logging.LogRecord("test", level, "test.py", 10, "Test message", (), None)
    record.asctime = "2024-01-01 00:00:00"

    output = formatter.format(record)
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

    # Strip ANSI color codes using a more robust approach
    import re

    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    cleaned_output = ansi_escape.sub("", output.strip())

    data = json.loads(cleaned_output)
    assert "ts" in data
    assert data["level"] == "INFO"
    assert data["msg"] == "Test message"
    assert data["data"] == test_data


def test_get_logger():
    """Test logger retrieval"""
    logger = get_logger("test_module")
    assert logger.name == "mcp_local_dev.test_module"


def test_configure_logging():
    """Test logging configuration"""
    configure_logging()
    logger = logging.getLogger("mcp_local_dev")

    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], logging.StreamHandler)
    assert not logger.propagate
