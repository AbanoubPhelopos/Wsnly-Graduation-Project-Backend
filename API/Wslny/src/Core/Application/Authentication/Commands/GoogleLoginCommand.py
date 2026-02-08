from dataclasses import dataclass
from src.Core.Application.Common.Interfaces.CQRS import ICommand
from src.Core.Application.Common.Models.Result import Result, Error
from src.Core.Application.Authentication.Common.AuthenticationResult import AuthenticationResult
from src.Core.Domain.Errors.DomainErrors import AuthErrors
from src.Core.Domain.Constants.Roles import Roles
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from google.oauth2 import id_token
from google.auth.transport import requests
import os

User = get_user_model()

@dataclass
class GoogleLoginCommand(ICommand):
    id_token: str

class GoogleLoginCommandHandler:
    def handle(self, command: GoogleLoginCommand) -> Result[AuthenticationResult]:
        try:
            # Verify the token
            # CLIENT_ID should be in settings
            id_info = id_token.verify_oauth2_token(command.id_token, requests.Request())
            
            email = id_info['email']
            first_name = id_info.get('given_name', '')
            last_name = id_info.get('family_name', '')
            
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'is_active': True,
                    'role': Roles.USER 
                }
            )
            
            refresh = RefreshToken.for_user(user)
            return Result.success(AuthenticationResult(
                user=user,
                token=str(refresh.access_token),
                refresh_token=str(refresh)
            ))
            
        except ValueError as e:
            return Result.failure(AuthErrors.GoogleTokenInvalid)
        except Exception as e:
            return Result.failure(Error("Auth.Error", str(e)))
