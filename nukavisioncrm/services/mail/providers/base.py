from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, List, Dict, Optional

@dataclass
class SendResult:
    ok: bool
    provider: str
    message_id: Optional[str] = None
    error: Optional[str] = None
    raw: Optional[dict] = None

class EmailProvider(Protocol):
    name: str
    def send(self,
             to: List[str],
             subject: str,
             html: str,
             text: Optional[str] = None,
             from_email: Optional[str] = None,
             from_name: Optional[str] = None,
             headers: Optional[Dict[str, str]] = None,
             tags: Optional[List[str]] = None) -> SendResult: ...
