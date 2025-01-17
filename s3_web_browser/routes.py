import boto3
import botocore
from flask import Flask, Response, redirect, render_template, request

from s3_web_browser.s3 import list_objects, parse_responses


def register_routes(app: Flask) -> None:  # noqa:C901
    @app.route("/", methods=["GET"])
    def index() -> str:
        s3 = boto3.resource("s3", **app.config["AWS_KWARGS"])
        all_buckets = s3.buckets.all()
        return render_template("index.html", buckets=all_buckets)

    @app.route("/buckets")
    def buckets() -> str:
        s3 = boto3.resource("s3", **app.config["AWS_KWARGS"])
        all_buckets = s3.buckets.all()
        return render_template("index.html", buckets=all_buckets)

    @app.route("/search/buckets/<bucket_name>", defaults={"path": ""})
    @app.route("/search/buckets/<bucket_name>/<path:path>")
    def search_bucket(bucket_name: str, path: str) -> str:
        page = request.args.get("page", 1, type=int)
        items_per_page = app.config["PAGE_ITEMS"]
        s3_client = boto3.client("s3", **app.config["AWS_KWARGS"])
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

        s3_client = boto3.client("s3", **app.config["AWS_KWARGS"])

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
                    temp_response = list_objects(
                        s3_client, bucket_name, path, app.config["PAGE_ITEMS"], "/", continuation_token
                    )
                    if not temp_response.get("IsTruncated"):
                        break
                    continuation_token = temp_response.get("NextContinuationToken")

            # Get the current page contents
            response = list_objects(s3_client, bucket_name, path, app.config["PAGE_ITEMS"], "/", continuation_token)
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
        s3_client = boto3.client("s3", **app.config["AWS_KWARGS"])
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": path},
            ExpiresIn=3600,
        )  # URL expires in 1 hour
        return redirect(url)
