import json
import hashlib

from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)


def dict_to_hash(d):
    json_string = json.dumps(d, sort_keys=True).encode()
    return hashlib.sha256(json_string).hexdigest()
