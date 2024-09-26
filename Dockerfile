FROM python:3.12.6-bookworm

ARG POETRY_VERSION=1.8.3
ENV POETRY_VERSION=$POETRY_VERSION
ENV POETRY_HOME=/usr/local
ENV POETRY_VIRTUALENVS_CREATE=false
RUN curl -sSL https://install.python-poetry.org | python -

WORKDIR /usr/src/app

COPY poetry.lock pyproject.toml /usr/src/app/

RUN poetry install

COPY . /usr/src/app/

RUN chown -R nobody /usr/src/app/

RUN usermod --home /tmp nobody
USER nobody

ENV PYTHONPATH=/usr/src/app
EXPOSE 8000

CMD ["gunicorn", "app:app"]
