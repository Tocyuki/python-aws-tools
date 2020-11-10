import boto3
from boto3.session import Session
import botocore


def start_session(profile, resource):
    try:
        session = Session(profile_name=profile)
        client = session.client(resource)
    except botocore.exceptions.ProfileNotFound:
        client = boto3.client(resource)

    return client

