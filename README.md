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
