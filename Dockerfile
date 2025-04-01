# Use an official slim Python image.
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy and install dependencies.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code.
COPY . .

# Expose port 8000 for Flask health check.
EXPOSE 8000

# Start the bot.
CMD ["python", "main.py"]
