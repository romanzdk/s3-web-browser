import boto3
from flask import Flask, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = "your_secure_random_key_here"


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        access_key = request.form["access_key"]
        secret_key = request.form["secret_key"]

        session["credentials"] = {
            "access_key": access_key,
            "secret_key": secret_key,
        }
        return redirect(url_for("buckets"))
    else:
        return render_template("index.html")


@app.route("/buckets")
def buckets():
    creds = session["credentials"]
    s3 = boto3.resource(
        "s3",
        aws_access_key_id=creds["access_key"],
        aws_secret_access_key=creds["secret_key"],
        region_name="eu-central-1",
    )
    buckets = s3.buckets.all()
    return render_template("buckets.html", buckets=buckets)


@app.route("/buckets/<bucket_name>", defaults={"path": ""})
@app.route("/buckets/<bucket_name>/<path:path>")
def view_bucket(bucket_name, path):
    creds = session["credentials"]
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=creds["access_key"],
        aws_secret_access_key=creds["secret_key"],
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
    app.run(debug=True)
