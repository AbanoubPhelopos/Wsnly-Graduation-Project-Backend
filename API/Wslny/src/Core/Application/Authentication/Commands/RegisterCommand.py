from dataclasses import dataclass
from src.Core.Application.Common.Interfaces.CQRS import ICommand
from src.Core.Application.Common.Models.Result import Result
from src.Core.Application.Authentication.Common.AuthenticationResult import AuthenticationResult
from src.Core.Domain.Errors.DomainErrors import AuthErrors
from src.Core.Domain.Constants.Roles import Roles
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
    gender: str = None
    address: str = None
    role: str = Roles.USER 

class RegisterCommandHandler:
    def handle(self, command: RegisterCommand) -> Result[AuthenticationResult]:
        if User.objects.filter(email=command.email).exists():
            return Result.failure(AuthErrors.UserExists)

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
