# S3 web browser

Description

## Setup

1. Install [poetry](https://python-poetry.org/)
2. `poetry install`

## Usage

### In Docker

1. Specify AWS credentials in `.env` file:
1. `docker build -t s3-browser .`
1. `docker run -it --rm -p 8000:8000 --network=host --env-file .env s3-browser`
1. Go to http://127.0.0.1:8000/ to browse through your files
