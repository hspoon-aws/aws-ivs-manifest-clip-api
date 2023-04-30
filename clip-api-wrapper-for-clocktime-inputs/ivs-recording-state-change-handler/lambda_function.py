import boto3
import json
import os

print('Loading function')
dynamo = boto3.client('dynamodb')
db_table_name = os.environ['DYNAMO_DB_TABLE_NAME'] #'ivs_recordings'


def respond(err, res=None):
    return {
        'statusCode': '400' if err else '200',
        'body': err.message if err else json.dumps(res),
        'headers': {
            'Content-Type': 'application/json',
        },
    }

    
def createTable(table_name):
    try:
        response = dynamo.create_table(
            AttributeDefinitions=[
                {
                    'AttributeName': 'recording_session_id',
                    'AttributeType': 'S',
                },
                {
                    'AttributeName': 'channel_arn',
                    'AttributeType': 'S',
                }
            ],
            KeySchema=[
                {
                    'AttributeName': 'channel_arn',
                    'KeyType': 'HASH',
                },
                {
                    'AttributeName': 'recording_session_id',
                    'KeyType': 'RANGE',
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5,
            },
            TableName=table_name,
        )
    except dynamo.exceptions.ResourceInUseException:
        # do something here as you require
        pass
    
    dynamo_table_exists_waiter = dynamo.get_waiter('table_exists')
    dynamo_table_exists_waiter.wait(TableName=table_name)
    
    return boto3.resource('dynamodb').Table(table_name)


def lambda_handler(event, context):
    '''Demonstrates a simple HTTP endpoint using API Gateway. You have full
    access to the request and response payload, including headers and
    status code.

    To scan a DynamoDB table, make a GET request with the TableName as a
    query string parameter. To put, update, or delete an item, make a POST,
    PUT, or DELETE request respectively, passing in the payload to the
    DynamoDB API as a JSON body.
    '''
    print("Received event: " + json.dumps(event, indent=2))
    
    if 'detail' not in event or 'recording_status' not in event['detail']:
        return respond(ValueError('Invalid data "{}"'.format(event)))
        
    if event['detail']["recording_status"] == 'Recording Start':
        print('Recording Start...')
        data = {
            "stream_id": event['detail']["stream_id"],
            "channel_arn": event['resources'][0],
            "channel_name": event['detail']["channel_name"],
            "account": event['account'],
            "region": event['region'],
            "recording_s3_bucket_name": event['detail']["recording_s3_bucket_name"],
            "recording_s3_key_prefix": event['detail']["recording_s3_key_prefix"],
            "recording_session_id": event['detail']["recording_session_id"],
            "recording_start_time": event['time'],
            "recording_end_time": None
        }
        print("Insert into DynamoDB : {}".format(data))
        table = createTable(db_table_name)
        res = table.put_item(
            Item=data
        )
        return respond(None, res)
        
        
    elif event['detail']["recording_status"] == 'Recording End':
        print('Recording End...')
        data = {
            "recording_status": event['detail']["recording_status"],
            "account": event['account'],
            "region": event['region'],
            "channel_arn": event['resources'][0],
            "channel_name": event['detail']["channel_name"],
            "recording_s3_bucket_name": event['detail']["recording_s3_bucket_name"],
            "recording_s3_key_prefix": event['detail']["recording_s3_key_prefix"],
            "stream_id": event['detail']["stream_id"],
            "recording_session_id": event['detail']["recording_session_id"],
            "recording_end_time": event['time'],
        }
        print("Get DynamoDB recording_session_id: {}".format(data['recording_session_id']))
        print("Update recording_end_time : {}".format(data['recording_end_time']))
        table = createTable(db_table_name)
        res = table.update_item(
                Key={'recording_session_id': data['recording_session_id'], 'channel_arn': data['channel_arn']},
                UpdateExpression="set recording_end_time=:t",
                ExpressionAttributeValues={
                    ':t': data['recording_end_time']},
                ReturnValues="UPDATED_NEW")
        return respond(None, res)
    

    # operations = {
    #     'DELETE': lambda dynamo, x: dynamo.delete_item(**x),
    #     'GET': lambda dynamo, x: dynamo.scan(**x),
    #     'POST': lambda dynamo, x: dynamo.put_item(**x),
    #     'PUT': lambda dynamo, x: dynamo.update_item(**x),
    # }

    # operation = event['httpMethod']
    # if operation in operations:
    #     payload = event['queryStringParameters'] if operation == 'GET' else json.loads(event['body'])
    #     return respond(None, operations[operation](dynamo, payload))
    # else:
    #     return respond(ValueError('Unsupported method "{}"'.format(operation)))
    
    return respond(ValueError('Unsupported event "{}"'.format(event)))
