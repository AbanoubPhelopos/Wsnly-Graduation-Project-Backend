from dataclasses import dataclass

@dataclass(frozen=True)
class Roles:
    ADMIN: str = "Admin"
    USER: str = "User"
