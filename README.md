# Medico24 Backend API

Enterprise-grade FastAPI backend for healthcare appointment management.

## 📚 Documentation

- **[Quick Start Guide](QUICKSTART.md)** - Get started in minutes
- **[Project Summary](PROJECT_SUMMARY.md)** - Complete overview of what's been built
- **[API Examples](API_EXAMPLES.md)** - Code examples for all endpoints
- **[Production Checklist](PRODUCTION_CHECKLIST.md)** - Pre-deployment checklist

## 🚀 Quick Links

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health
- **Metrics**: http://localhost:8000/metrics

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy Core
- **Migrations**: Alembic
- **Authentication**: JWT + Google OAuth
- **Caching**: Redis
- **Containerization**: Docker
- **CI/CD**: GitHub Actions
- **Package Management**: uv

## Features

- ✅ RESTful API with FastAPI
- ✅ PostgreSQL database with connection pooling
- ✅ JWT authentication with refresh tokens
- ✅ Google OAuth integration
- ✅ Redis caching and session management
- ✅ Request rate limiting
- ✅ Structured logging with structlog
- ✅ Prometheus metrics
- ✅ Database migrations with Alembic
- ✅ Docker containerization
- ✅ Comprehensive test suite
- ✅ Type hints and validation with Pydantic
- ✅ CORS middleware
- ✅ Error handling and custom exceptions

## Setup

1. **Clone and navigate to the project**:

   ```bash
   cd medico24-backend
   ```

2. **Create virtual environment**:

   ```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1  # Windows
   source venv/bin/activate      # Linux/Mac
   ```

3. **Install dependencies**:

   ```bash
   pip install uv
   uv pip install -e ".[dev]"
   ```

4. **Configure environment**:

   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. **Run migrations**:

   ```bash
   alembic upgrade head
   ```

6. **Start the server**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## Development

- **Run tests**: `pytest`
- **Format code**: `black app tests`
- **Lint**: `ruff check app tests`
- **Type check**: `mypy app`

## Docker

```bash
# Build and run with Docker Compose
docker-compose up --build

# Run in production mode
docker-compose -f docker-compose.yml up -d
```

## API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## Environment Variables

See `.env.example` for all required environment variables.

## License

Proprietary - Medico24
