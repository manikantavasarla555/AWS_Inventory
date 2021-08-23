#!/usr/bin/python3
import os
import csv
import datetime
import itertools
import json
import os.path

import boto3  # pip install boto3
import jmespath

from inputs import *
from pathlib import Path


ec2_data = []
ebs_data = []
elb_data = []
s3_data = []
lambda_data = []


def generate_report(filename, columns, data):
    # write data to csv file with headers
    today = datetime.datetime.today().strftime('%Y-%m-%d')
    Path(today).mkdir(parents=True, exist_ok=True)
    output = list(itertools.chain(*data))
    #file_name = today + "/" + filename + "-" + today + ".csv"
    file_name = today + "/" + filename + ".csv"
    with open(file_name, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(output)


def generate_ec2_report(profile):
    for region in regions:
        print(f"Getting instances for the region: {region}")
        current_session = boto3.Session(profile_name=profile, region_name=region)
        ec2_client = current_session.client('ec2')
        paginator = ec2_client.get_paginator('describe_instances')

        if not asset_ids:
            response = paginator.paginate().build_full_result()
            if response['Reservations']:
                output = jmespath.search(
                    "Reservations[].Instances[].[NetworkInterfaces[0].OwnerId, [Tags[?Key=='Name'].Value][0][0], InstanceId, InstanceType,State.Name, Placement.AvailabilityZone, PrivateIpAddress, PublicIpAddress, PublicDnsName, VpcId, SubnetId, KeyName, [Tags[?Key=='tr:environment-type'].Value][0][0], [Tags[?Key=='tr:resource-owner'].Value][0][0], [Tags[?Key=='tr:project-name'].Value][0][0], [Tags[?Key=='tr:application-asset-insight-id'].Value][0][0]]",
                    response)
                # filter instances missing the asset id tags
                details_list = []
                for d in output:
                    if not d[15]:
                        details_list.append(d)
                ec2_data.append(details_list)
        else:
            response = paginator.paginate(Filters=[{
                'Name': 'tag:tr:application-asset-insight-id',
                'Values': asset_ids
            }]).build_full_result()

            if response['Reservations']:
                output = jmespath.search(
                    "Reservations[].Instances[].[NetworkInterfaces[0].OwnerId, [Tags[?Key=='Name'].Value][0][0], InstanceId, InstanceType,State.Name, Placement.AvailabilityZone, PrivateIpAddress, PublicIpAddress, PublicDnsName, VpcId, SubnetId, KeyName, [Tags[?Key=='tr:environment-type'].Value][0][0], [Tags[?Key=='tr:resource-owner'].Value][0][0], [Tags[?Key=='tr:project-name'].Value][0][0], [Tags[?Key=='tr:application-asset-insight-id'].Value][0][0]]",
                    response)
                ec2_data.append(output)


def write_ec2_report():
    columns = ['AccountID', 'Instance Name', 'InstanceID', 'Type', 'State', 'AZ', 'PrivateIP', 'PublicIP',
               'Public DNS Name',
               'VPC ID', 'Subnet ID', 'KeyPair', 'Env type', 'Resource Owner', 'Project name', 'Asset ID']
    filename = "ec2-inventory-report"
    generate_report(filename, columns, ec2_data)


def generate_ebs_report(profile, account_num):
    for region in regions:
        print(f"Getting ebs volumes for the region: {region}")
        current_session = boto3.Session(profile_name=profile, region_name=region)
        ec2_client = current_session.client('ec2')
        paginator = ec2_client.get_paginator('describe_volumes')

        if not asset_ids:
            response = paginator.paginate().build_full_result()
            if response['Volumes']:
                output = jmespath.search(
                    "Volumes[].[VolumeId, [Tags[?Key=='Name'].Value][0][0], VolumeType, State, SnapshotId, AvailabilityZone, Iops, Encrypted, MultiAttachEnabled, Size, CreateTime, [Tags[?Key=='tr:environment-type'].Value][0][0], [Tags[?Key=='tr:resource-owner'].Value][0][0], [Tags[?Key=='tr:project-name'].Value][0][0], [Tags[?Key=='tr:application-asset-insight-id'].Value][0][0]]",
                    response)

                output2 = []
                for ebs in output:
                    if not ebs[14]:
                        # aadding account number in data
                        ebs.insert(0, account_num)
                        output2.append(ebs)

                ebs_data.append(output2)
        else:
            response = paginator.paginate(Filters=[{
                'Name': 'tag:tr:application-asset-insight-id',
                'Values': asset_ids
            }]).build_full_result()

            if response['Volumes']:
                output = jmespath.search(
                    "Volumes[].[VolumeId, [Tags[?Key=='Name'].Value][0][0], VolumeType, State, SnapshotId, AvailabilityZone, Iops, Encrypted, MultiAttachEnabled, Size, CreateTime, [Tags[?Key=='tr:environment-type'].Value][0][0], [Tags[?Key=='tr:resource-owner'].Value][0][0], [Tags[?Key=='tr:project-name'].Value][0][0], [Tags[?Key=='tr:application-asset-insight-id'].Value][0][0]]",
                    response)

                # aadding account number in data
                output2 = []
                for ebs in output:
                    ebs.insert(0, account_num)
                    output2.append(ebs)
                ebs_data.append(output2)


def write_ebs_report():
    columns = ['AccountId', 'VolumeId', 'Volume Name', 'VolumeType', 'State', 'SnapshotId', 'AZ', 'Iops', 'Encrypted',
               'MultiAttachEnabled',
               'Size', 'CreateTime', 'Env type', 'Resource Owner', 'Project name', 'Asset ID']
    filename = "ebs-inventory-report"
    generate_report(filename, columns, ebs_data)


def generate_elb_report(profile, account_num):
    for region in regions:
        print(f"Getting lbs for the region: {region}")
        current_session = boto3.Session(profile_name=profile, region_name=region)
        elb_client = current_session.client('elbv2')
        paginator = elb_client.get_paginator('describe_load_balancers')
        response = paginator.paginate().build_full_result()

        if response['LoadBalancers']:
            output = jmespath.search(
                "LoadBalancers[].[Type, LoadBalancerName, DNSName, Scheme, VpcId, AvailabilityZones, LoadBalancerArn]",
                response)

            output2 = []
            # Get tags
            for elb in output:
                tags_resp = elb_client.describe_tags(ResourceArns=[elb[6]])
                tags = tags_resp['TagDescriptions'][0] or {}

                elb_tags = {}
                for t in tags.get('Tags', []):
                    elb_tags[t.get('Key')] = t.get('Value')

                elb.insert(0, account_num)
                elb.append(elb_tags.get("tr:environment-type", ""))
                elb.append(elb_tags.get("tr:resource-owner", ""))
                elb.append(elb_tags.get("tr:application-asset-insight-id", ""))

                if elb_tags.get("tr:application-asset-insight-id") in asset_ids:
                    output2.append(elb)
                elif not asset_ids and elb_tags.get("tr:application-asset-insight-id") is None:
                    output2.append(elb)
                else:
                    pass

            elb_data.append(output2)


def write_elb_report():
    columns = ['AccountID', 'LoadBalancer Type', 'ELB name', 'DNS name', 'Scheme', 'VPCId', 'AvailabilityZones',
               'LoadBalancerArn', 'Env type', 'Resource Owner', 'Asset ID']
    filename = "elb-inventory-report"
    generate_report(filename, columns, elb_data)


def generate_s3_report(profile, account_num):
    print("Getting s3 buckets...")
    current_session = boto3.Session(profile_name=profile, region_name='us-east-1')
    s3_client = current_session.client('s3')

    response = s3_client.list_buckets(Filters=[{
        'Name': 'tag:tr:application-asset-insight-id',
        'Values': asset_ids
    }])

    if response['Buckets']:
        output = jmespath.search(
            "Buckets[].[Name, CreationDate]",
            response)

        output2 = []
        for s3 in output:
            # aadding account number in data
            s3.insert(0, account_num)
            try:
                r = s3_client.get_bucket_tagging(Bucket=s3[1])
                s3_tags = {t['Key']: t['Value'] for t in r['TagSet']}
            except Exception as e:
                s3_tags = {}
            s3.append(s3_tags.get("tr:environment-type", ""))
            s3.append(s3_tags.get("tr:resource-owner", ""))
            s3.append(s3_tags.get("tr:project-name", ""))
            s3.append(s3_tags.get("tr:application-asset-insight-id", ""))

            if s3_tags.get("tr:application-asset-insight-id") in asset_ids:
                output2.append(s3)
            elif not asset_ids and s3_tags.get("tr:application-asset-insight-id") is None:
                output2.append(s3)
            else:
                pass

        s3_data.append(output2)


def write_s3_report():
    columns = ['AccountId', 'Name', 'CreationDate', 'Env type', 'Resource Owner', 'Project name', 'Asset ID']
    filename = "s3-inventory-report"
    generate_report(filename, columns, s3_data)


def generate_lambda_report(profile, account_num):
    for region in regions:
        print(f"Getting lambda functions for the region: {region}")
        current_session = boto3.Session(profile_name=profile, region_name=region)
        lambda_client = current_session.client('lambda')
        paginator = lambda_client.get_paginator('list_functions')

        response = paginator.paginate().build_full_result()
        if response['Functions']:
            output = jmespath.search(
                "Functions[].[FunctionName, Runtime, Role, Timeout, MemorySize, Version, VpcConfig.VpcId, VpcConfig.SubnetIds, VpcConfig.SecurityGroupIds, State, LastUpdateStatus]",
                response)

            output2 = []
            for lambda_func in output:
                lambda_func.insert(0, account_num)

                r = lambda_client.get_function(
                    FunctionName=lambda_func[1]
                )

                # l_tags = {t['Key']: t['Value'] for t in r['TagSet']}
                l_tags = r.get('Tags', {})

                lambda_func.append(l_tags.get("tr:environment-type", ""))
                lambda_func.append(l_tags.get("tr:resource-owner", ""))
                lambda_func.append(l_tags.get("tr:project-name", ""))
                lambda_func.append(l_tags.get("tr:application-asset-insight-id", ""))

                if l_tags.get("tr:application-asset-insight-id") in asset_ids:
                    output2.append(lambda_func)
                elif not asset_ids and l_tags.get("tr:application-asset-insight-id") is None:
                    output2.append(lambda_func)
                else:
                    pass

            lambda_data.append(output2)


def write_lambda_report():
    columns = ['AccountId', 'FunctionName', 'Runtime', 'Role', 'Timeout', 'MemorySize', 'Version', 'VPCId', 'SubnetIDs',
               'SecurityGroupIds',
               'State', 'LastUpdateStatus', 'Env type', 'Resource Owner', 'Project name', 'Asset ID']
    filename = "lambda-inventory-report"
    generate_report(filename, columns, lambda_data)


def main():
    # fetch instance details using accounts
    for account_details in accounts:
        print(f"Getting instances for the account: {account_details['account']} profile: {account_details['profile']}")
        generate_ec2_report(account_details['profile'])
        generate_ebs_report(account_details['profile'], account_details['account'])
        generate_elb_report(account_details['profile'], account_details['account'])
        generate_s3_report(account_details['profile'], account_details['account'])
        generate_lambda_report(account_details['profile'], account_details['account'])

    write_ec2_report()
    write_ebs_report()
    write_elb_report()
    write_s3_report()
    write_lambda_report()


if __name__ == "__main__":
    print("aws-inventory script started...")
    main()
    print("aws-inventory script completed !!")
