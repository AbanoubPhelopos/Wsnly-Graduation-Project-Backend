# Wslny API

The `Wslny` backend is a Django-based application structured with **Clean Architecture** principles and implements the **CQRS (Command-Query Responsibility Segregation)** pattern. It aims to provide a robust, scalable backend for the Wslny platform.

## Architecture & Design Patterns

The project follows a multilayered class library approach, ensuring separation of concerns and maintainability.

### Folder Structure (`src/`)

- **Core/Domain**:
  - The innermost layer.
  - Contains **Entities**, **Value Objects**, and core business logic.
  - No dependencies on Application, Infrastructure, or Presentation layers.

- **Core/Application**:
  - Contains **Use Cases**, **CQRS Handlers**, **Interfaces**, and **DTOs**.
  - **Common/Intefraces**: Defines abstractions (e.g., `ICommand`, `IQuery`).
  - **Common/Models**: Includes the **Result Pattern** wrapper for standardized API responses.
  - Dependent only on Domain.

- **Infrastructure**:
  - Implements interfaces defined in the Application layer (e.g., Repositories, External Services, Email, File Storage).
  - Handles database interactions.
  - Dependent on Domain and Application.

- **Presentation**:
  - The entry point for the application (Django project configuration).
  - Contains **Controllers** (Views/ViewSets) that map HTTP requests to Application commands/queries.
  - Handles routing (`urls.py`) and configuration (`settings.py`).

### Key Patterns

#### CQRS (Command-Query Responsibility Segregation)
Operations are split into two distinct models:
- **Commands**: Modify state (Create, Update, Delete). Return a `Result` indicating success or failure.
- **Queries**: Read state. Return data without side effects.

Defines `ICommand`, `IQuery`, `ICommandHandler`, and `IQueryHandler` interfaces in `src/Core/Application/Common/Interfaces/CQRS.py`.

#### Result Pattern
A standardized wrapper for all service responses, found in `src/Core/Application/Common/Models/Result.py`.
- Encapsulates success/failure state.
- Returns type-safe data or a list of errors.
- Avoids using Exceptions for control flow.

## Getting Started

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (optional but recommended)
- PostgreSQL (if running locally without Docker)

### Running with Docker (Recommended)

1. Navigate to the project directory:
   ```bash
   cd API/Wslny
   ```

2. Build and start the containers:
   ```bash
   docker-compose up --build
   ```

The API will be available at `http://localhost:8000`.

### Running Locally

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure database settings in `src/Presentation/settings.py` if not using the default Docker setup.

4. Apply migrations:
   ```bash
   python manage.py migrate
   ```

5. Run the server:
   ```bash
   python manage.py runserver
   ```

## Development Workflow

1. Define **Entities** in `Core/Domain`.
2. Define **DTOs** and **Interfaces** in `Core/Application`.
3. Implement **Command/Query Handlers** in `Core/Application`.
4. Implement **Infrastructure** (Repositories) in `Infrastructure`.
5. Expose functionality via **API Views** in `Presentation`.
