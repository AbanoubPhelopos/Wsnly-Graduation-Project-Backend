from dataclasses import dataclass
from src.Core.Application.Common.Interfaces.CQRS import IQuery
from src.Core.Application.Common.Models.Result import Result, Error
from django.contrib.auth import get_user_model

User = get_user_model()

@dataclass
class UserProfileDto:
    email: str
    first_name: str
    last_name: str
    mobile_number: str
    gender: str
    address: str
    role: str

@dataclass
class GetProfileQuery(IQuery[UserProfileDto]):
    user_id: int

class GetProfileQueryHandler:
    def handle(self, query: GetProfileQuery) -> Result[UserProfileDto]:
        try:
            user = User.objects.get(pk=query.user_id)
            return Result.success(UserProfileDto(
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                mobile_number=user.mobile_number,
                gender=user.gender,
                address=user.address,
                role=user.role
            ))
        except User.DoesNotExist:
            return Result.failure(Error("User.NotFound", "User not found"))
