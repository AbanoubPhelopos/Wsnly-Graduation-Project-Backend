from dataclasses import dataclass
from src.Core.Application.Common.Interfaces.CQRS import ICommand
from src.Core.Application.Common.Models.Result import Result, Error
from src.Core.Application.Authentication.Common.AuthenticationResult import AuthenticationResult
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

@dataclass
class RegisterCommand(ICommand):
    email: str
    password: str
    first_name: str
    last_name: str
    mobile_number: str
    role: str
    gender: str = None
    address: str = None

class RegisterCommandHandler:
    def handle(self, command: RegisterCommand) -> Result[AuthenticationResult]:
        if User.objects.filter(email=command.email).exists():
            return Result.failure(Error("User.Exists", "User with this email already exists"))

        user = User.objects.create_user(
            email=command.email,
            password=command.password,
            first_name=command.first_name,
            last_name=command.last_name,
            mobile_number=command.mobile_number,
            gender=command.gender,
            address=command.address,
            role=command.role
        )

        refresh = RefreshToken.for_user(user)
        
        return Result.success(AuthenticationResult(
            user=user,
            token=str(refresh.access_token),
            refresh_token=str(refresh)
        ))
