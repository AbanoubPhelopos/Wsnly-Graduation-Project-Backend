from dataclasses import dataclass
from src.Core.Application.Common.Interfaces.CQRS import ICommand
from src.Core.Application.Common.Models.Result import Result
from src.Core.Domain.Constants.Roles import Roles
from src.Core.Domain.Errors.DomainErrors import UserErrors
from django.contrib.auth import get_user_model

User = get_user_model()

@dataclass
class ChangeUserRoleCommand(ICommand):
    user_id: int
    new_role: str

class ChangeUserRoleCommandHandler:
    def handle(self, command: ChangeUserRoleCommand) -> Result[bool]:
        if command.new_role not in [Roles.ADMIN, Roles.USER]:
             return Result.failure(UserErrors.InvalidRole)

        try:
            user = User.objects.get(pk=command.user_id)
            user.role = command.new_role
            
            # Update permissions based on role if needed
            if command.new_role == Roles.ADMIN:
                user.is_staff = True
                user.is_superuser = True
            else:
                user.is_staff = False
                user.is_superuser = False
                
            user.save()
            return Result.success(True)
        except User.DoesNotExist:
            return Result.failure(UserErrors.NotFound)
