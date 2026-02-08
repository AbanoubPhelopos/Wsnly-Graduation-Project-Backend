from dataclasses import dataclass
from typing import List
from src.Core.Application.Common.Interfaces.CQRS import IQuery
from src.Core.Application.Common.Models.Result import Result
from django.contrib.auth import get_user_model

User = get_user_model()

@dataclass
class UserDto:
    id: int
    email: str
    first_name: str
    last_name: str
    role: str

@dataclass
class GetUsersQuery(IQuery[List[UserDto]]):
    pass

class GetUsersQueryHandler:
    def handle(self, query: GetUsersQuery) -> Result[List[UserDto]]:
        users = User.objects.all().values('id', 'email', 'first_name', 'last_name', 'role')
        user_dtos = [UserDto(**user) for user in users]
        return Result.success(user_dtos)
