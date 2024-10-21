import dataclasses
import os

import boto3
import botocore
import humanize
from flask import Flask, render_template, request

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


@dataclasses.dataclass
class S3Entry:
    """Representation of S3 object."""

    name: str
    type: str
    url: str = ""
    size: str = ""
    date_modified: str = ""


def parse_responses(responses: list, s3_client: botocore.client.BaseClient, bucket_name: str, search_param: str) -> list[S3Entry]:
    contents: set[S3Entry] = set()
    for response in responses:
        # Add folders to contents
        if "CommonPrefixes" in response:
            for item in response["CommonPrefixes"]:
                contents.add(
                    S3Entry({
                        "name": item["Prefix"],
                        "type": "folder"
                    })
                )

        # Add files to contents
        if "Contents" in response:
            for item in response["Contents"]:
                if not item["Key"].endswith("/"):
                    url = s3_client.generate_presigned_url(
                        "get_object",
                        Params={"Bucket": bucket_name, "Key": item["Key"]},
                        ExpiresIn=3600,
                    )  # URL expires in 1 hour
                    contents.add(
                        S3Entry({
                            "name": f'{bucket_name}/{item["Key"]}',
                            "type": "file",
                            "url": url,
                            "size": humanize.naturalsize(item["Size"]),
                            "date_modified": item["LastModified"],
                        })
                    )

    contents_list = list(contents)
    if search_param:
        contents_list = list(filter(lambda x: search_param in x.name, contents_list))
    return sorted(contents_list, key=lambda x: x.type, reverse=True)


def list_objects(s3_client: botocore.client.BaseClient, bucket_name: str, path: str, delimiter: str = "") -> list[dict]:
    responses = []
    list_params = {"Bucket": bucket_name, "Prefix": path}
    if delimiter:
        list_params["Delimiter"] = "/"

    while True:
        response = s3_client.list_objects_v2(**list_params)
        responses.append(response)
        if response["IsTruncated"]:
            list_params["ContinuationToken"] = response["NextContinuationToken"]
        else:
            break

    return responses


@app.route("/search//buckets/<bucket_name>", defaults={"path": ""})
@app.route("/search/buckets/<bucket_name>/<path:path>")
def search_bucket(bucket_name: str, path: str) -> str:
    s3_client = boto3.client("s3", **AWS_KWARGS)
    responses = []
    try:
        responses.extend(list_objects(s3_client, bucket_name, path))
        responses.extend(list_objects(s3_client, bucket_name, path, "/"))
    except botocore.exceptions.ClientError as e:
        match e.response["Error"]["Code"]:
            case "AccessDenied":
                return render_template(
                    "error.html",
                    error="You do not have permission to access this bucket.",
                )
            case "NoSuchBucket":
                return render_template("error.html", error="The specified bucket does not exist.")
            case _:
                return render_template("error.html", error=f"An unknown error occurred: {e}")
    except Exception as e:  # noqa: BLE001
        return render_template("error.html", error=f"An unknown error occurred: {e}")


    search_param = request.args.get("search", "")
    contents = parse_responses(responses, s3_client, bucket_name, search_param)
    return render_template(
        "bucket_contents.html",
        contents=contents,
        bucket_name=bucket_name,
        path=path,
        search_param=search_param,
    )


@app.route("/buckets/<bucket_name>", defaults={"path": ""})
@app.route("/buckets/<bucket_name>/<path:path>")
def view_bucket(bucket_name: str, path: str) -> str:
    s3_client = boto3.client("s3", **AWS_KWARGS)
    responses = []
    try:
        responses.extend(list_objects(s3_client, bucket_name, path, "/"))
    except botocore.exceptions.ClientError as e:
        match e.response["Error"]["Code"]:
            case "AccessDenied":
                return render_template(
                    "error.html",
                    error="You do not have permission to access this bucket.",
                )
            case "NoSuchBucket":
                return render_template("error.html", error="The specified bucket does not exist.")
            case _:
                return render_template("error.html", error=f"An unknown error occurred: {e}")
    except Exception as e:  # noqa: BLE001
        return render_template("error.html", error=f"An unknown error occurred: {e}")

    search_param = request.args.get("search", "")
    contents = parse_responses(responses, s3_client, bucket_name, search_param)
    return render_template(
        "bucket_contents.html",
        contents=contents,
        bucket_name=bucket_name,
        path=path,
        search_param=search_param,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)  # noqa: S104
