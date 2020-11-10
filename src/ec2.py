import argparse
import boto3
from botocore.exceptions import ClientError
from launch_template import *
from session import *


def create_instance_from_template(args):
    launch_template_versions = describe_launch_template_versions(args.template_name, args.profile)
    template_id = launch_template_versions[0]['LaunchTemplateId']
    template_version = launch_template_versions[0]['VersionNumber']

    ec2 = boto3.resource('ec2')
    response = ec2.create_instances(
        LaunchTemplate={
            'LaunchTemplateId': template_id,
            'Version': str(template_version),
        },
        MaxCount=1,
        MinCount=1,
        SubnetId=args.subnet_id,
    )
    for i in response:
        print(f'create instance({i.id}) was successful.')


def get_healthy_instance_ip(args):
    client = start_session(args.profile, 'elbv2')

    try:
        target_group = client.describe_target_groups(
            Names=[f'{args.target_group}']
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'TargetGroupNotFound':
            print('Please enter the exact target group name.')
        else:
            print(f'Unexpected error: {e}')
    else:
        target_hosts = client.describe_target_health(
            TargetGroupArn=target_group['TargetGroups'][0]['TargetGroupArn']
        )

        instance_ids = []
        for target_host in target_hosts['TargetHealthDescriptions']:
            if target_host['TargetHealth']['State'] == 'healthy':
                instance_ids.append(target_host['Target']['Id'])

        client = boto3.client('ec2')
        instances = client.describe_instances(
            InstanceIds=instance_ids
        )

        for instance in instances['Reservations']:
            ip = instance['Instances'][0]['PrivateIpAddress']
            for tag in instance['Instances'][0]['Tags']:
                if tag['Key'] == 'Name':
                    name_tag = tag['Value']
            print(name_tag, ip)


def describe_ec2(args):
    client = start_session(args.profile, 'ec2')
    if args.filter:
        response = client.describe_instances(
            Filters=[{
                'Name': 'tag:Name',
                'Values': [f'*{args.filter}*']
            }],
        )
    else:
        response = client.describe_instances()

    for instance in response['Reservations']:
        try:
            for instance_tag in instance['Instances'][0]['Tags']:
                if instance_tag['Key'] == 'Name':
                    name = instance_tag['Value']
            private_ip = instance['Instances'][0]['PrivateIpAddress']
            instance_id = instance['Instances'][0]['InstanceId']
            status = instance['Instances'][0]['State']['Name']
            print(instance_id, private_ip, name, status)
        except KeyError:
            pass


def main():
    parser = argparse.ArgumentParser(
        description='describe instance info'
    )
    subparsers = parser.add_subparsers()

    parser_list = subparsers.add_parser('list', help='see `list -h`')
    parser_list.add_argument('--filter', help='filter of describe')
    parser_list.add_argument('--profile', help='set aws profile', default='default')
    parser_list.set_defaults(handler=describe_ec2)

    parser_create = subparsers.add_parser('create', help='see `create -h`')
    parser_create.add_argument('--template-name', help='launch template name', required=True)
    parser_create.add_argument('--subnet-id', help='specify vpc subnet id', required=True)
    parser_create.add_argument('--profile', help='set aws profile', default='default')
    parser_create.set_defaults(handler=create_instance_from_template)

    parser_get_healthy_instance_ip = subparsers.add_parser(
        'get-healthy', help='see `list -h`'
    )
    parser_get_healthy_instance_ip.add_argument(
        '--target-group',
        help='exact target group name.',
        required=True
    )
    parser_get_healthy_instance_ip.add_argument(
        '--profile',
        help='set aws profile',
        default='default'
    )
    parser_get_healthy_instance_ip.set_defaults(handler=get_healthy_instance_ip)

    args = parser.parse_args()
    if hasattr(args, 'handler'):
        args.handler(args)
    else:
        parser.print_help()
