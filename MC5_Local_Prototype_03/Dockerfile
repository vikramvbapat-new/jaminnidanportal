FROM python:3.11-slim

# Create a non-root user (Hugging Face Spaces runs as user 1000)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR $HOME/app

# Install Python dependencies
COPY --chown=user:user requirements-deploy.txt $HOME/app/requirements.txt
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy application source code
COPY --chown=user:user ./app $HOME/app/app

# Hugging Face Spaces standard port is 7860
EXPOSE 7860

# Run FastAPI with Uvicorn on 0.0.0.0:7860
CMD ["python", "-m", "uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "7860"]
