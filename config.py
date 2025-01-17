import os
from typing import ClassVar


class Config:  # noqa: D101
    SECRET_KEY = os.getenv("SECRET_KEY", "your_default_secret_key")  # Replace with a secure key in production
    DEBUG = os.getenv("DEBUG", "False")

    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "eu-central-1")
    AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", None)

    AWS_KWARGS: ClassVar[dict[str, str | None]] = {
        "aws_access_key_id": AWS_ACCESS_KEY_ID,
        "aws_secret_access_key": AWS_SECRET_ACCESS_KEY,
        "region_name": AWS_DEFAULT_REGION,
    }

    if AWS_ENDPOINT_URL:
        AWS_KWARGS["endpoint_url"] = AWS_ENDPOINT_URL

    PAGE_ITEMS = int(os.getenv("PAGE_ITEMS", "300"))
