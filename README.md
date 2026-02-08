# Wslny Project

**Wslny** is a comprehensive transportation platform designed to streamline commutes and logistics through a modern digital ecosystem for the Greatest Cairo transportation.

The project is divided into two main components: a powerful backend API and a versatile frontend suite including a web admin panel and a mobile application.

## 📂 Repository Structure

The repository is organized into the following main directories:

### 1. `API` (Backend)
The backend service responsible for business logic, data management, and authentication.

*   **Technology**: Python, Django, Django Rest Framework.
*   **Architecture**: Clean Architecture with CQRS (Command Query Responsibility Segregation).
*   **Key Features**:
    *   **Authentication**: Secure JWT-based auth with Google Login support.
    *   **Role Management**: Distinct roles for Users and Admins.
    *   **Containerization**: Fully Dockerized for consistent deployment.
*   **Documentation**: See [API/README.md](API/README.md) for setup and API details.

### 2. `UI` (Frontend)
This directory houses the user interfaces for different platforms:

*   **Web Application**:
    *   **Purpose**: Functions as the **Admin Panel** for managing users, roles, and system oversight.
    *   **Target Users**: Administrators.
    
*   **Mobile Application**:
    *   **Technology**: Flutter.
    *   **Purpose**: The primary interface for end-users to interact with the Wslny platform.
    *   **Target Users**: General Users (Android & iOS).

## 🚀 Getting Started

To get started with the project, please refer to the specific `README.md` files within the `API` and `UI` directories for detailed installation and running instructions.