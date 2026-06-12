# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install uv for dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY core/ ./core/
COPY sparkplug_b/ ./sparkplug_b/
COPY main.py ./

# Set Python to unbuffered mode for proper logging
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["uv", "run", "main.py"]
