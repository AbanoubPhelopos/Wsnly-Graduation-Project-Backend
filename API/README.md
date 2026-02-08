# Wslny API

The **Wslny API** is a robust, scalable backend service built with **Django Rest Framework** (DRF), designed to power the Wslny platform.

It is architected using **Clean Architecture** principles and implements the **CQRS (Command-Query Responsibility Segregation)** pattern to ensure separation of concerns, maintainability, and testability.

## 🚀 Key Features

*   **Clean Architecture**: Separation into `Domain`, `Application`, `Infrastructure`, and `Presentation` layers.
*   **CQRS Pattern**: Distinct models for reading (Queries) and writing (Commands) data.
*   **Result Pattern**: A standardized wrapper for all API responses, ensuring consistent error handling and type safety.
*   **Authentication & Identity**:
    *   JWT (JSON Web Tokens) Authentication.
    *   Google OAuth Integration.
    *   Custom User Model (Email-based) with specific profile fields.
    *   Role-Based Access Control (Admin/User).
*   **Containerization**: Fully Dockerized setup with `docker-compose` for easy deployment and development.
*   **Automated Weeding**: Automatic creation of a default Admin user on startup.

## 🏗 Architecture Overview

The project follows a "Multilayer Class Library" style adapted for Django:

### Folder Structure (`src/`)

*   **Core/Domain**:
    *   The heart of the application. Contains **Entities**, **Value Objects**, **Constants** (e.g., Roles), and **Errors**.
    *   Completely independent of other layers.
*   **Core/Application**:
    *   Orchestrates application logic.
    *   Contains **CQRS Handlers** (Commands & Queries), **Interfaces**, **DTOs**, and the **Result Pattern**.
    *   Dependent only on the Domain layer.
*   **Infrastructure**:
    *   Implements interfaces defined in the Application layer.
    *   Handles database access, external APIs (e.g., Google Auth), and Identity configuration.
    *   Contains persistence models and management commands.
*   **Presentation**:
    *   The entry point (Django Project).
    *   Contains **Views** (Controllers), **URLs**, `settings.py`, and `permissions.py`.
    *   Maps HTTP requests to Application Commands/Queries.

## 🔐 Authentication & Roles

The system supports two primary roles:
1.  **User**: Standard user access. Can register manually or via Google used for general app usage.
2.  **Admin**: System administrator. Has access to user management and role assignment.

### Auth Endpoints
*   `POST /api/auth/register`: Register a new user.
*   `POST /api/auth/login`: Login with email/password.
*   `POST /api/auth/google-login`: Login/Register with Google ID Token.
*   `GET /api/auth/profile`: Get current user profile.

### Admin Endpoints
*   `POST /api/admin/change-role`: Change a user's role (e.g., promote to Admin).
*   `GET /api/admin/users`: List all users in the system.

## 🛠 Getting Started

### Prerequisites
*   Docker & Docker Compose

### Running with Docker (Recommended)

1.  **Clone the repository** and navigate to `API/Wslny`.
2.  **Start the application**:
    ```bash
    docker-compose up --build
    ```
    *   This will build the Python image, start PostgreSQL, apply migrations, and **seed the default admin user automatically**.

3.  **Access the API**:
    *   The server runs at `http://localhost:8000`.

## 💻 Development Workflow

1.  **Define Domain**: Add entities or constants in `Core/Domain`.
2.  **Define Contract**: Create Interfaces and DTOs in `Core/Application`.
3.  **Implement Logic**: Create Command/Query Handlers in `Core/Application`.
4.  **Implement Infrastructure**: detailed implementation in `Infrastructure` (if needed).
5.  **Expose API**: Create Views and URLs in `Presentation`.

## 📦 Tech Stack

*   **Language**: Python 3.11
*   **Framework**: Django 4.2+, Django Rest Framework
*   **Auth**: SimpleJWT, Google Auth
*   **Database**: PostgreSQL 15
*   **Containerization**: Docker
