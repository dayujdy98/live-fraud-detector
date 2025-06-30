#!/usr/bin/env python3
"""
Script to delete all object versions and delete markers from S3 bucket
"""
import boto3


def empty_bucket_completely(bucket_name):
    """Delete all objects, versions, and delete markers from bucket"""
    s3 = boto3.client("s3")

    # Delete all object versions
    print(f"Deleting all object versions from {bucket_name}...")

    paginator = s3.get_paginator("list_object_versions")
    pages = paginator.paginate(Bucket=bucket_name)

    objects_to_delete = []
    for page in pages:
        # Collect versions
        if "Versions" in page:
            for version in page["Versions"]:
                objects_to_delete.append(
                    {"Key": version["Key"], "VersionId": version["VersionId"]}
                )

        # Collect delete markers
        if "DeleteMarkers" in page:
            for delete_marker in page["DeleteMarkers"]:
                objects_to_delete.append(
                    {
                        "Key": delete_marker["Key"],
                        "VersionId": delete_marker["VersionId"],
                    }
                )

        # Delete in batches of 1000 (AWS limit)
        if len(objects_to_delete) >= 1000:
            delete_objects(s3, bucket_name, objects_to_delete)
            objects_to_delete = []

    # Delete remaining objects
    if objects_to_delete:
        delete_objects(s3, bucket_name, objects_to_delete)

    print(f"Bucket {bucket_name} is now completely empty")


def delete_objects(s3, bucket_name, objects):
    """Delete a batch of objects"""
    if not objects:
        return

    response = s3.delete_objects(
        Bucket=bucket_name, Delete={"Objects": objects, "Quiet": False}
    )

    deleted = len(response.get("Deleted", []))
    errors = len(response.get("Errors", []))
    print(f"Deleted {deleted} objects, {errors} errors")

    if errors > 0:
        for error in response["Errors"]:
            print(f"Error deleting {error['Key']}: {error['Message']}")


if __name__ == "__main__":
    bucket_name = "live-fraud-detector-terraform-state"
    empty_bucket_completely(bucket_name)
