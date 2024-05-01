# S3 web browser

Description

## Setup

1. Install [poetry](https://python-poetry.org/)
2. `poetry install`

## Usage

### In Docker

1. Specify AWS credentials in `.env` file:
1. `docker build -t s3-browser .`
1. `docker run -it --rm -p 5000:5000 --env-file .env s3-browser`
1. Go to http://192.168.x.x:5000/ (see output of the container) to browse through your files

### Locally

1. Specify AWS credentials via environment variables:

   ```bash
   export AWS_ACCESS_KEY_ID=...
   export AWS_SECRET_ACCESS_KEY=...
   ```

1. Run the app `poetry run python app.py`
1. Go to http://127.0.0.1:5000/ to browse through your files
