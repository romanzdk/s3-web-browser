import dataclasses

import botocore
import humanize


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
    page_items: int,
    delimiter: str = "",
    page_token: str | None = None,
) -> dict:
    list_params = {"Bucket": bucket_name, "Prefix": path, "MaxKeys": page_items}
    if delimiter:
        list_params["Delimiter"] = "/"
    if page_token:
        list_params["ContinuationToken"] = page_token

    return s3_client.list_objects_v2(**list_params)
