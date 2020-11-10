import argparse
from ami import *
from session import *


def describe_launch_template_versions(template_name, profile):
    client = start_session(profile, 'ec2')
    try:
        response = client.describe_launch_template_versions(
            LaunchTemplateName=template_name,
        )
    except botocore.exceptions.ClientError:
        return None
    else:
        return response['LaunchTemplateVersions']


def create_launch_template_from_latest_ami(ami_name, template_name, profile):
    launch_template_versions = describe_launch_template_versions(template_name, profile)
    images = describe_sorted_images(ami_name, profile)
    latest_image = images[0]['ImageId']
    if latest_image != launch_template_versions[0]['LaunchTemplateData']['ImageId']:
        client = start_session(profile, 'ec2')
        response = client.create_launch_template_version(
            LaunchTemplateData={
                'ImageId': latest_image,
            },
            LaunchTemplateId=launch_template_versions[0]['LaunchTemplateId'],
            SourceVersion=str(launch_template_versions[0]['VersionNumber']),
        )
        return response
    else:
        return None


def change_default_version(template_name, profile):
    client = start_session(profile, 'ec2')

    try:
        describe_response = client.describe_launch_templates(
            LaunchTemplateNames=[template_name],
        )
    except botocore.exceptions.ClientError:
        raise Exception('例外が発生しました')
    else:
        if describe_response['LaunchTemplates'][0]['DefaultVersionNumber'] != describe_response['LaunchTemplates'][0]['LatestVersionNumber']:
            modify_response = client.modify_launch_template(
                LaunchTemplateId=describe_response['LaunchTemplates'][0]['LaunchTemplateId'],
                DefaultVersion=str(describe_response['LaunchTemplates'][0]['LatestVersionNumber']),
            )
            return modify_response['LaunchTemplate']
        else:
            return None


def update_launch_template(args):
    create_response = create_launch_template_from_latest_ami(args.ami_name, args.template_name, args.profile)
    change_default_version_response = change_default_version(args.template_name, args.profile)

    if create_response:
        print(create_response)
    else:
        print('Launch Template is already updated with latest AMI.')

    if change_default_version_response:
        print('You have successfully changed the default version to the latest version of the launch template.')
        print(change_default_version_response)
    else:
        print('Launch Template default version is already latest version.')


def list_launch_templates(args):
    try:
        launch_templates = describe_launch_template_versions(args.template_name, args.profile)
        for launch_template in launch_templates:
            print(
                f"version: {str(launch_template['VersionNumber']).zfill(3)}",
                launch_template['CreateTime'],
                launch_template['LaunchTemplateId'],
                launch_template['LaunchTemplateData']['ImageId'],
            )
    except TypeError:
        print('Please enter the exact launch template name.')


def prune_launch_templates(args):
    launch_template_versions = describe_launch_template_versions(args.template_name, args.profile)
    sorted_images = describe_sorted_images(args.ami_name, args.profile)
    count = 0

    for launch_template in launch_template_versions:
        flag = ['True' for sorted_image in sorted_images if launch_template['LaunchTemplateData']['ImageId'] in sorted_image['ImageId']]
        if not flag:
            client = start_session(args.profile, 'ec2')
            response = client.delete_launch_template_versions(
                LaunchTemplateId=launch_template['LaunchTemplateId'],
                Versions=[
                    str(launch_template['VersionNumber']),
                ]
            )

            print(response)
            count += 1

    if count == 0:
        print('Launch Template is already prune.')


def main():
    parser = argparse.ArgumentParser(
        description='update launch template ami & default version.'
    )
    subparsers = parser.add_subparsers()

    parser_update = subparsers.add_parser('update', help='see `update -h`')
    parser_update.add_argument('--ami-name', help='ami name tag', required=True)
    parser_update.add_argument('--template-name', help='exact launch template name', required=True)
    parser_update.add_argument('--profile', help='set aws profile', default='default')
    parser_update.set_defaults(handler=update_launch_template)

    parser_list = subparsers.add_parser('list', help='see `list -h`')
    parser_list.add_argument('--template-name', help='exact launch template name', required=True)
    parser_list.add_argument('--profile', help='set aws profile', default='default')
    parser_list.set_defaults(handler=list_launch_templates)

    parser_prune = subparsers.add_parser('prune', help='see `prune -h`')
    parser_prune.add_argument('--ami-name', help='ami name tag', required=True)
    parser_prune.add_argument('--template-name', help='launch template name', required=True)
    parser_prune.add_argument('--profile', help='set aws profile', default='default')
    parser_prune.set_defaults(handler=prune_launch_templates)

    args = parser.parse_args()
    if hasattr(args, 'handler'):
        args.handler(args)
    else:
        parser.print_help()
