import argparse
from session import *


def describe_sorted_images(filter, profile='default'):
    client = start_session(profile, 'ec2')
    response = client.describe_images(
        Filters=[{
            'Name': 'tag:Name',
            'Values': [f'*{filter}*']
        }],
        Owners=['self']
    )

    sorted_response = sorted(
        response['Images'],
        key=lambda x:x['CreationDate'],
        reverse=True
    )

    return sorted_response


def prune_ami(args):
    sorted_images = describe_sorted_images(args.filter)
    name_tag_check = []
    for sorted_image in sorted_images:
        for tag in sorted_image['Tags']:
            if tag['Key'] == 'Name':
                name_tag_check.append(tag['Value'])

    if len(set(name_tag_check)) > 1:
        print('The following "Name" tag was detected.')
        for name_tag in set(name_tag_check):
            print(name_tag)
        print('Please filter the "Name" tag to be unique.')

        return

    flag = False
    client = start_session(args.profile, 'ec2')
    for i, image in enumerate(sorted_images, 1):
        ami_id = image['ImageId']
        snapshot_id = image['BlockDeviceMappings'][0]['Ebs']['SnapshotId']
        if i > args.generation:
            flag = True
            unregister_ami_response = client.deregister_image(
                ImageId=ami_id,
            )
            if unregister_ami_response['ResponseMetadata']['HTTPStatusCode'] == 200:
                print(f"Delete {ami_id} request ID {unregister_ami_response['ResponseMetadata']['RequestId']} was succesful!!!")
            else:
                print(f"Delete {ami_id} request ID {unregister_ami_response['ResponseMetadata']['RequestId']} was failed!!!")

            delete_snapshot_response = client.delete_snapshot(
                SnapshotId=snapshot_id,
            )
            if delete_snapshot_response['ResponseMetadata']['HTTPStatusCode'] == 200:
                print(f"Delete {snapshot_id} request ID {delete_snapshot_response['ResponseMetadata']['RequestId']} was succesful!!!")
            else:
                print(f"Delete {snapshot_id} request ID {delete_snapshot_response['ResponseMetadata']['RequestId']} was failed!!!")

    if not flag:
        print('AMI is already prune.')


def list_ami(args):
    sorted_images = describe_sorted_images(args.filter)
    for i, sorted_image in enumerate(sorted_images, 1):
        for tag in sorted_image['Tags']:
            if tag['Key'] == 'Name':
                name_tag = tag['Value']
        print(
            str(i).zfill(3),
            sorted_image['CreationDate'],
            sorted_image['Name'],
            name_tag,
            sorted_image['ImageId'],
            sorted_image['BlockDeviceMappings'][0]['Ebs']['SnapshotId']
        )


def main():
    parser = argparse.ArgumentParser(
        description='list & prune ami.'
    )
    subparsers = parser.add_subparsers()

    parser_prune = subparsers.add_parser('prune', help='see `prune -h`')
    parser_prune.add_argument('--filter', help='filter of describe', required=True)
    parser_prune.add_argument('--generation', type=int, help='default 7 generations', default=7)
    parser_prune.add_argument('--profile', help='set aws profile', default='default')
    parser_prune.set_defaults(handler=prune_ami)

    parser_list = subparsers.add_parser('list', help='see `list -h`')
    parser_list.add_argument('--filter', help='filter of describe', required=True)
    parser_list.add_argument('--profile', help='set aws profile', default='default')
    parser_list.set_defaults(handler=list_ami)

    args = parser.parse_args()
    if hasattr(args, 'handler'):
        args.handler(args)
    else:
        parser.print_help()
