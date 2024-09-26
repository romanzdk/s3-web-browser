import os

import boto3
from flask import Flask, render_template

app = Flask(__name__)
app.secret_key = "your_secure_random_key_here"  # noqa: S105

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "eu-central-1")
AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", None)

AWS_KWARGS = {
    "aws_access_key_id": AWS_ACCESS_KEY_ID,
    "aws_secret_access_key": AWS_SECRET_ACCESS_KEY,
    "region_name": AWS_DEFAULT_REGION,
}

if AWS_ENDPOINT_URL:
    AWS_KWARGS["endpoint_url"] = AWS_ENDPOINT_URL


@app.route("/", methods=["GET"])
def index() -> str:
    s3 = boto3.resource("s3", **AWS_KWARGS)
    buckets = s3.buckets.all()
    return render_template("index.html", buckets=buckets)


@app.route("/buckets")
def buckets() -> str:
    s3 = boto3.resource("s3", **AWS_KWARGS)
    buckets = s3.buckets.all()
    return render_template("index.html", buckets=buckets)


@app.route("/buckets/<bucket_name>", defaults={"path": ""})
@app.route("/buckets/<bucket_name>/<path:path>")
def view_bucket(bucket_name: str, path: str) -> str:
    s3_client = boto3.client("s3", **AWS_KWARGS)

    try:
        response = s3_client.list_objects_v2(
            Bucket=bucket_name, Prefix=path, Delimiter="/"
        )
    except botocore.exceptions.ClientError as e:
        match e.response["Error"]["Code"]:
            case "AccessDenied":
                return render_template(
                    "error.html",
                    error="You do not have permission to access this bucket.",
                )
            case "NoSuchBucket":
                return render_template(
                    "error.html", error="The specified bucket does not exist."
                )
            case _:
                return render_template(
                    "error.html", error=f"An unknown error occurred: {e}"
                )
    except Exception as e:  # noqa: BLE001
        return render_template("error.html", error=f"An unknown error occurred: {e}")
    contents = []

    # Add folders to contents
    if "CommonPrefixes" in response:
        for item in response["CommonPrefixes"]:
            contents.append({"name": item["Prefix"], "type": "folder"})  # noqa: PERF401

    # Add files to contents
    if "Contents" in response:
        for item in response["Contents"]:
            if not item["Key"].endswith("/"):  # Ignore directories
                url = s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": bucket_name, "Key": item["Key"]},
                    ExpiresIn=3600,
                )  # URL expires in 1 hour
                contents.append({"name": item["Key"], "type": "file", "url": url})

    return render_template(
        "bucket_contents.html",
        contents=contents,
        bucket_name=bucket_name,
        path=path,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)  # noqa: S104
