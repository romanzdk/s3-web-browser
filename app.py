from flask import Flask, request, render_template, redirect, url_for, session
import boto3

app = Flask(__name__)
app.secret_key = "your_secure_random_key_here"


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        access_key = request.form["access_key"]
        secret_key = request.form["secret_key"]
        session_token = request.form.get(
            "session_token", None
        )  # Optional, defaults to None if not provided

        # Store credentials in session
        session["credentials"] = {
            "access_key": access_key,
            "secret_key": secret_key,
            "session_token": session_token,
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
        aws_session_token=creds.get("session_token"),  # Safely access using get
    )
    buckets = s3.buckets.all()
    return render_template("buckets.html", buckets=buckets)


@app.route("/buckets/<bucket_name>", defaults={"path": ""})
@app.route("/buckets/<bucket_name>/<path:path>")
def view_bucket(bucket_name, path):
    creds = session["credentials"]
    s3 = boto3.resource(
        "s3",
        aws_access_key_id=creds["access_key"],
        aws_secret_access_key=creds["secret_key"],
        aws_session_token=creds.get("session_token"),
    )
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=creds["access_key"],
        aws_secret_access_key=creds["secret_key"],
        aws_session_token=creds.get("session_token"),
    )
    print(f"{path=}")
    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=path, Delimiter="/")

    print(f"{response=}")
    try:
        contents = [obj["Prefix"] for obj in response["CommonPrefixes"]]
    except KeyError:
        contents = [obj["Key"] for obj in response["Contents"]]

    print(contents)
    print([item for item in contents])
    return render_template(
        "bucket_contents.html", contents=contents, bucket_name=bucket_name, path=path
    )


if __name__ == "__main__":
    app.run(debug=True)
