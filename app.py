import os

import boto3
from flask import Flask, render_template

app = Flask(__name__)
app.secret_key = "your_secure_random_key_here"

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")


@app.route("/", methods=["GET"])
def index():
    s3 = boto3.resource(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name="eu-central-1",
    )
    buckets = s3.buckets.all()
    return render_template("index.html", buckets=buckets)


@app.route("/buckets")
def buckets():
    s3 = boto3.resource(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name="eu-central-1",
    )
    buckets = s3.buckets.all()
    return render_template("index.html", buckets=buckets)


@app.route("/buckets/<bucket_name>", defaults={"path": ""})
@app.route("/buckets/<bucket_name>/<path:path>")
def view_bucket(bucket_name, path):
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name="eu-central-1",
    )

    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=path, Delimiter="/")
    contents = []

    # Add folders to contents
    if "CommonPrefixes" in response:
        for item in response["CommonPrefixes"]:
            contents.append({"name": item["Prefix"], "type": "folder"})

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
        "bucket_contents.html", contents=contents, bucket_name=bucket_name, path=path
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
