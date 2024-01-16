import os
import json
import boto3
import csv
import datetime
from dateutil.tz import tzlocal

wks = boto3.client('workspaces')
sns = boto3.client('sns')
s3  = boto3.client('s3')
now = datetime.datetime.now()
now = now.replace(tzinfo = tzlocal())
exec_date_str = now.strftime("%m-%d-%Y")
exec_timestamp_str = now.strftime("%m-%d-%Y_%H:%M:%S")
sns_topic_arn = os.environ['sns_topic_arn']
s3_bucket_name = os.environ['s3_bucket_name']

def timedelta_to_string(td:datetime):
    days = str(td.days)
    hours = str(td.seconds//3600)
    mins = str((td.seconds//60)%60)
    length = days+"d" + hours+"h" + mins+"m"
    return length

def get_username(workspace_id:str):
    workspace_info = wks.describe_workspaces(WorkspaceIds=[workspace_id])
    username = workspace_info["Workspaces"][0]["UserName"]
    return username

def get_tags(workspace_id:str):
    response = wks.describe_tags(ResourceId=workspace_id)
    tag_list = response["TagList"]
    result = []
    for t in tag_list:
        item = {}
        item[t['Key']]=t['Value']
        result.append(item)
    return result

def send_email(raw_data:dict,arn:str):
    #Build email data
    idle_workspaces_data = []
    for i in raw_data["WorkspacesConnectionStatus"]:
        entry = f'{i["UserName"]}@{i["WorkspaceId"]}({i["IdleTime"]})'
        idle_workspaces_data.append(entry)
    #send email notification using SNS    
    response = sns.publish(
        TargetArn=arn,
        Subject=f'Worksapces Usage Report {exec_date_str}: user@workspace_id(IdleTime)',
        Message=json.dumps({'default': json.dumps(idle_workspaces_data)}),
        MessageStructure='json'
    )
    return response

def uploads3(raw_data:dict,bucket:str):
    #Write raw_data into a file
    with open(f'/tmp/mycsv.csv', 'w', newline ='') as f:
        thewriter = csv.writer(f)
        thewriter.writerow(['WorkspaceId','UserName','IdleTime',"Tags"])
        for i in raw_data['WorkspacesConnectionStatus']:
            thewriter.writerow([i['WorkspaceId'],
                                i['UserName'],
                                i['IdleTime'],
                                i['Tags']])
    #Upload the file to S3 bucket
    response = s3.upload_file('/tmp/mycsv.csv', 
                              bucket, 
                              f'reports/{exec_timestamp_str}.csv')
    return response

def get_idletime():
    #Get list of all workspaces connect status
    wks_conn_stat = wks.describe_workspaces_connection_status()
    wks_conn_stat_cp = wks_conn_stat.copy()
    #Build report data
    for i in wks_conn_stat_cp["WorkspacesConnectionStatus"]:
        i["IdleTime"] = ""
        i["UserName"] = ""
        #Get never been connected workspaces
        if "LastKnownUserConnectionTimestamp" not in i.keys():    
            i["IdleTime"] = "n/a"
            i["UserName"] = get_username(workspace_id=i["WorkspaceId"])
            i["Tags"] = get_tags(workspace_id=i["WorkspaceId"])
            print (f'{i["IdleTime"]} {i["UserName"]} {i["WorkspaceId"]}')
        #Get other workspaces 
        elif "LastKnownUserConnectionTimestamp" in i.keys():
            timestamp = i["LastKnownUserConnectionTimestamp"]
            delta = now - timestamp
            i["IdleTime"] = timedelta_to_string(delta)
            i["UserName"] = get_username(workspace_id=i["WorkspaceId"])
            i["Tags"] = get_tags(workspace_id=i["WorkspaceId"])
            print (f'{i["IdleTime"]} {i["UserName"]} {i["WorkspaceId"]}')
        else:
            print(f'error pops on {i["WorkspaceId"]}')
    return wks_conn_stat_cp

def lambda_handler(event, context):
    # TODO implement
    data = get_idletime()
    uploads3(raw_data=data, bucket=s3_bucket_name)
    return send_email(raw_data=data,arn=sns_topic_arn)

data = get_idletime()
uploads3(raw_data=data, bucket=s3_bucket_name)
send_email(raw_data=data,arn=sns_topic_arn)
