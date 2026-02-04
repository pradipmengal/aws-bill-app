# AWS Region-wise Billing Dashboard

A modern, Dockerized Python application for viewing AWS billing usage by region.

## Method 1: Run with Docker (Recommended)

This is the easiest way to run the application as it handles all dependencies for you.

1. **Build the container:**
   ```bash
   docker-compose build
   ```

2. **Run the application:**
   ```bash
   docker-compose up
   ```

3. **Access the dashboard:**
   Open your browser to [http://localhost:8000](http://localhost:8000).

By default, the application runs in **Demo Mode**, so you can explore the UI without AWS credentials.

## Method 2: Run Locally (Python)

If you prefer to run it directly on your machine:

1. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the server:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Access the dashboard:**
   Open your browser to [http://localhost:8000](http://localhost:8000).

## Configuration

- **Demo Mode:** By default, `USE_DEMO_DATA=true` is set in `docker-compose.yml`.
- **AWS Credentials:** To use real data, you can either:
  - Enter your credentials in the Login screen on the UI (securely passed to the backend).
  - Or configure them in `docker-compose.yml` (not recommended for committed code).
