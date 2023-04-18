# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3
from botocore.config import Config
import json
import os
import uuid
import logging
from aws_lambda_powertools import Tracer

tracer = Tracer()  # Sets service via POWERTOOLS_SERVICE_NAME env var

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ['TABLE_NAME']
TOPIC_ARN = os.environ['TOPIC_ARN']

config = Config(connect_timeout=5, read_timeout=5, retries={'max_attempts': 1})
dynamodb = boto3.client('dynamodb', config=config)
sns = boto3.client('sns', config=config)

REQUIRED_INT_FIELDS = ['duration', 'distance']
REQUIRED_FLOAT_FIELDS = ['fare']
REQUIRED_STR_FIELDS = ['from', 'to', 'customer']

def is_invalid(request):
    for field in REQUIRED_INT_FIELDS:
        if not isinstance(request.get(field, None), int):
            print('Expecting integer for argument: {}'.format(field))
            return True

    for field in REQUIRED_FLOAT_FIELDS:
        if not isinstance(request.get(field, None), float):
            print('Expecting float for argument: {}'.format(field))
            return True

    for field in REQUIRED_STR_FIELDS:
        if not isinstance(request.get(field, None), str):
            print('Expecting string for argument: {}'.format(field))
            return True

    return False

@tracer.capture_lambda_handler
def lambda_handler(event, context):
    print('EVENT: {}'.format(json.dumps(event)))

    request = json.loads(event['body'])
    print('The request loaded ' + str(request))

    if is_invalid(request):
        return {
            'statusCode': 400,
            'body': json.dumps({})
        }

    print('Request is valid!')

    id = str(uuid.uuid4())
    request['id'] = id

    response = dynamodb.put_item(
        TableName=TABLE_NAME,
        Item={
            'id': {'S': id},
            'from': {'S': request['from']},
            'to': {'S': request['to']},
            'duration': {'N': str(request['duration'])},
            'distance': {'N': str(request['distance'])},
            'customer': {'S': request['customer']},
            'fare': {'N': str(request['fare'])}
        }
    )

    response = sns.publish(
        TopicArn=TOPIC_ARN,
        Message=json.dumps(request),
        MessageAttributes = {
            'fare': {
                'DataType': 'Number',
                'StringValue': str(request['fare'])
            },
            'distance': {
                'DataType': 'Number',
                'StringValue': str(request['distance'])
            }
        }
    )

    return {
        'statusCode': 201,
        'body': json.dumps({
            "id": id
        })
    }
