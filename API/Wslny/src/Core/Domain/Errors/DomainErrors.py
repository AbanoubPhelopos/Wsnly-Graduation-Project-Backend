from src.Core.Application.Common.Models.Result import Error

class AuthErrors:
    InvalidCredentials = Error("Auth.InvalidCredentials", "Invalid email or password.")
    GoogleTokenInvalid = Error("Auth.GoogleTokenInvalid", "Invalid Google ID token.")
    GoogleAuthFailed = Error("Auth.GoogleAuthFailed", "Google authentication failed.")
    UserExists = Error("Auth.UserExists", "User with this email already exists.")

class UserErrors:
    NotFound = Error("User.NotFound", "User not found.")
    InvalidRole = Error("User.InvalidRole", "Invalid role specified.")
    Unauthorized = Error("User.Unauthorized", "You are not authorized to perform this action.")
