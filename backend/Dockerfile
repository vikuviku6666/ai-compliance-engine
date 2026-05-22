FROM python:3.12-slim

WORKDIR /app

# Install uv for fast package management
RUN pip install uv

# Copy dependencies definitions
COPY pyproject.toml .
# Copy lock file if it exists, otherwise it will just copy pyproject.toml
COPY uv.lock* .

# Install dependencies using uv into the system environment
RUN uv pip install --system -e .

# Copy the rest of the backend code
COPY backend/app ./app

# Expose port
EXPOSE 8000

# Run the FastAPI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
