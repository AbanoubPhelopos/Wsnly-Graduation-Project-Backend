from dataclasses import dataclass
from typing import Optional

@dataclass
class AuthenticationResult:
    user: object 
    token: str
    refresh_token: str
