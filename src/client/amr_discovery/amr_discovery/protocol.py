"""Bentuk pesan UDP discovery (request/reply) dan (de)serialisasi JSON-nya.

Kontrak ini yang harus dicocokkan oleh sisi app Flutter.
"""

from dataclasses import asdict, dataclass
from typing import Optional
import json

SCHEMA_VERSION = 1
DEFAULT_PORT = 41234

REQUEST_TYPE = 'AMR_DISCOVER'
REPLY_TYPE = 'AMR_DISCOVER_REPLY'


@dataclass
class DiscoveryRequest:
    nonce: Optional[str]


def parse_request(raw: bytes) -> Optional[DiscoveryRequest]:
    """Return None untuk paket apapun yang tidak valid, alih-alih raise."""
    try:
        data = json.loads(raw.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None

    if not isinstance(data, dict) or data.get('type') != REQUEST_TYPE:
        return None

    nonce = data.get('nonce')
    return DiscoveryRequest(nonce=nonce if isinstance(nonce, str) else None)


@dataclass
class RobotStatusSnapshot:
    """Semua field Optional: None berarti data belum/tidak tersedia."""
    mode: Optional[str] = None
    error_code: Optional[str] = None
    battery_percent: Optional[float] = None
    battery_voltage: Optional[float] = None
    battery_voltage_max: Optional[float] = None
    is_charging: Optional[bool] = None
    status_message: Optional[str] = None


def build_reply(robot_id: str, ip: Optional[str], nonce: Optional[str],
                 timestamp: float, status: RobotStatusSnapshot) -> dict:
    return {
        'type': REPLY_TYPE,
        'schema': SCHEMA_VERSION,
        'nonce': nonce,
        'robot_id': robot_id,
        'ip': ip,
        'timestamp': timestamp,
        **asdict(status),
    }


def encode_reply(reply: dict) -> bytes:
    return json.dumps(reply).encode('utf-8')
