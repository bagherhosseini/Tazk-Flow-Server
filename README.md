# Tazk Flow Server - Django Python server for Task Management

The Tazk Flow Server is the backend for the Tazk Flow task management app. Built with Django, it powers the app's complex workflows, team collaboration, and real-time task updates. It provides RESTful APIs for seamless integration with the React Native frontend.

## Key Features
- **Custom Workflows**: Manage and store customizable task statuses for projects.
- **Team Collaboration**: Handle user roles, task assignments, and team communications.
- **Task Tracking**: Support for comments, attachments, and task updates.
- **API Integration**: RESTful APIs for connecting with the React Native frontend.
- **Scalable Architecture**: Designed to handle growing teams and projects.

## Tech Stack
- **Django**: High-level Python web framework for backend development.
- **Django REST Framework (DRF)**: For building RESTful APIs.
- **PostgreSQL**: Relational database for storing task and user data.
- **Celery + Redis**: For handling asynchronous tasks (e.g., notifications).
- **Docker**: Simplified deployment and environment management.

## Installation

Follow these steps to set up the Tazk Flow Server on your local machine:

### Prerequisites
- Python 3.8 or higher installed on your system.
- PostgreSQL installed and configured.
- Redis installed for Celery (optional but recommended).
- [Docker](https://www.docker.com/) (optional for containerized setup).

### Steps

1. **Clone the Repository**:
   ```bash
    git clone https://github.com/yourusername/tazk-flow-server.git
2. **Create a Virtual Environment and Install Dependencies**:
   ```bash
    python -m venv env
    source env/bin/activate  # On Windows, use `env\Scripts\activate`
    pip install -r requirements.txt
3. **Set Up Environment Variables: Create a .env file in the project root and configure the following**:
   ```bash
    DJANGO_SECRET_KEY=your-secret-key

    CLERK_SECRET_KEY=your-CLERK-secret-key
    CLERK_JWT_KEY=your-CLERK-JWT-KEY
    CLERK_INSTANCE_ID=your-CLERK-INSTANCE-ID
    CLERK_PEM_PUBLIC_KEY=your-CLERK-PEM-PUBLIC-KEY

    DEBUG=True
    DJANGO_DEBUG=True

    DATABASE_NAME=your-DATABASE-NAME
    DATABASE_USER=your-DATABASE-USER
    DATABASE_PASSWORD=your-DATABASE-PASSWORD
    DATABASE_HOST=your-DATABASE-HOST
    DATABASE_PORT=your-DATABASE-PORT
4. **Run Migrations**:
   ```bash
    python manage.py migrate
5. **Start the Development Server**:
   ```bash
    python manage.py runserver 0.0.0.0:8000
