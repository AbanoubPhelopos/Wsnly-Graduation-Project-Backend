from typing import Generic, TypeVar, Optional, List, Any
from dataclasses import dataclass, field

T = TypeVar('T')

@dataclass
class Error:
    code: str
    message: str

@dataclass
class Result(Generic[T]):
    is_success: bool
    data: Optional[T] = None
    errors: List[Error] = field(default_factory=list)
    
    @property
    def is_failure(self) -> bool:
        return not self.is_success
    
    @classmethod
    def success(cls, data: T = None) -> 'Result[T]':
        return cls(is_success=True, data=data)
    
    @classmethod
    def failure(cls, error: Error) -> 'Result[T]':
        return cls(is_success=False, errors=[error])

    @classmethod
    def failure_multiple(cls, errors: List[Error]) -> 'Result[T]':
        return cls(is_success=False, errors=errors)
