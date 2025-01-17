import dataclasses
import os

import boto3
import botocore
import humanize
from flask import Flask, Response, redirect, render_template, request

app = Flask(__name__)
app.secret_key = "your_secure_random_key_here"  # noqa: S105

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "eu-central-1")
AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", None)

PAGE_ITEMS = int(os.getenv("PAGE_ITEMS", "300"))

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
    all_buckets = s3.buckets.all()
    return render_template("index.html", buckets=all_buckets)


@app.route("/buckets")
def buckets() -> str:
    s3 = boto3.resource("s3", **AWS_KWARGS)
    all_buckets = s3.buckets.all()
    return render_template("index.html", buckets=all_buckets)


@dataclasses.dataclass(eq=True, frozen=True)
class S3Entry:
    """Representation of S3 object."""

    name: str
    type: str
    size: str = ""
    date_modified: str = ""


def parse_responses(responses: list, search_param: str) -> list[S3Entry]:
    contents: set[S3Entry] = set()
    for response in responses:
        # Add folders to contents
        if isinstance(response, dict) and "CommonPrefixes" in response:
            for item in response["CommonPrefixes"]:
                contents.add(S3Entry(name=item["Prefix"], type="folder"))

        # Add files to contents
        if isinstance(response, dict) and "Contents" in response:
            for item in response["Contents"]:
                if not item["Key"].endswith("/"):
                    contents.add(
                        S3Entry(
                            name=item["Key"],
                            type="file",
                            size=humanize.naturalsize(item["Size"]),
                            date_modified=item["LastModified"],
                        )
                    )

    contents_list = list(contents)
    if search_param:
        # TODO: use regex
        contents_list = list(filter(lambda x: search_param.lower() in x.name.lower(), contents_list))
    return sorted(contents_list, key=lambda x: (x.type == "file", x.name.lower()))


def list_objects(
    s3_client: botocore.client.BaseClient,
    bucket_name: str,
    path: str,
    delimiter: str = "",
    page_token: str | None = None,
) -> dict:
    list_params = {"Bucket": bucket_name, "Prefix": path, "MaxKeys": PAGE_ITEMS}
    if delimiter:
        list_params["Delimiter"] = "/"
    if page_token:
        list_params["ContinuationToken"] = page_token

    return s3_client.list_objects_v2(**list_params)


@app.route("/search/buckets/<bucket_name>", defaults={"path": ""})
@app.route("/search/buckets/<bucket_name>/<path:path>")
def search_bucket(bucket_name: str, path: str) -> str:
    page = request.args.get("page", 1, type=int)
    items_per_page = PAGE_ITEMS
    s3_client = boto3.client("s3", **AWS_KWARGS)
    paginator = s3_client.get_paginator("list_objects_v2")
    all_entries = []
    all_prefixes = []

    try:
        # Collect all objects and folders
        for page_iterator in paginator.paginate(Bucket=bucket_name, Prefix=path):
            if "Contents" in page_iterator:
                all_entries = [
                    {"Key": item["Key"], "Size": item["Size"], "LastModified": item["LastModified"]}
                    for item in page_iterator["Contents"]
                    if not item["Key"].endswith("/")
                ]

        for page_iterator in paginator.paginate(Bucket=bucket_name, Prefix=path, Delimiter="/"):
            if "CommonPrefixes" in page_iterator:
                all_prefixes.extend(page_iterator["CommonPrefixes"])

        # Create response structure
        response = {"Contents": all_entries, "CommonPrefixes": all_prefixes}

        search_param = request.args.get("search", "")
        contents = parse_responses([response], search_param)

        # Calculate pagination
        total_items = len(contents)
        total_pages = (total_items + items_per_page - 1) // items_per_page
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        paginated_contents = contents[start_idx:end_idx]

        return render_template(
            "bucket_contents.html",
            contents=paginated_contents,
            bucket_name=bucket_name,
            path=path,
            search_param=search_param,
            current_page=page,
            total_pages=total_pages,
        )

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


@app.route("/buckets/<bucket_name>", defaults={"path": ""})
@app.route("/buckets/<bucket_name>/<path:path>")
def view_bucket(bucket_name: str, path: str) -> str:
    page = request.args.get("page", 1, type=int)
    items_per_page = 500

    s3_client = boto3.client("s3", **AWS_KWARGS)

    # Get total objects count for current prefix level only
    paginator = s3_client.get_paginator("list_objects_v2")
    total_objects = 0
    for page_iterator in paginator.paginate(Bucket=bucket_name, Prefix=path, Delimiter="/"):
        # Count folders (CommonPrefixes)
        if "CommonPrefixes" in page_iterator:
            total_objects += len(page_iterator["CommonPrefixes"])
        # Count files (Contents) but exclude folder markers
        if "Contents" in page_iterator:
            total_objects += sum(1 for obj in page_iterator["Contents"] if not obj["Key"].endswith("/"))

    total_pages = (total_objects + items_per_page - 1) // items_per_page

    try:
        # Calculate continuation token for the requested page
        continuation_token = None
        if page > 1:
            temp_response = None
            for _ in range(page - 1):
                temp_response = list_objects(s3_client, bucket_name, path, "/", continuation_token)
                if not temp_response.get("IsTruncated"):
                    break
                continuation_token = temp_response.get("NextContinuationToken")

        # Get the current page contents
        response = list_objects(s3_client, bucket_name, path, "/", continuation_token)
        contents = parse_responses([response], request.args.get("search", ""))

        return render_template(
            "bucket_contents.html",
            contents=contents,
            bucket_name=bucket_name,
            path=path,
            search_param=request.args.get("search", ""),
            current_page=page,
            total_pages=total_pages,
        )
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


@app.route("/download/buckets/<bucket_name>/<path:path>")
def download_file(bucket_name: str, path: str) -> Response:
    s3_client = boto3.client("s3", **AWS_KWARGS)
    url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket_name, "Key": path},
        ExpiresIn=3600,
    )  # URL expires in 1 hour
    return redirect(url)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)  # noqa: S104
