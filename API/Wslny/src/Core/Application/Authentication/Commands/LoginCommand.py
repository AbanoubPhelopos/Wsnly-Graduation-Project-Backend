from dataclasses import dataclass
from src.Core.Application.Common.Interfaces.CQRS import ICommand
from src.Core.Application.Common.Models.Result import Result
from src.Core.Application.Authentication.Common.AuthenticationResult import AuthenticationResult
from src.Core.Domain.Errors.DomainErrors import AuthErrors
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

@dataclass
class LoginCommand(ICommand):
    email: str
    password: str

class LoginCommandHandler:
    def handle(self, command: LoginCommand) -> Result[AuthenticationResult]:
        user = authenticate(email=command.email, password=command.password)
        
        if user is None:
            return Result.failure(AuthErrors.InvalidCredentials)
            
        refresh = RefreshToken.for_user(user)
        
        return Result.success(AuthenticationResult(
            user=user,
            token=str(refresh.access_token),
            refresh_token=str(refresh)
        ))
