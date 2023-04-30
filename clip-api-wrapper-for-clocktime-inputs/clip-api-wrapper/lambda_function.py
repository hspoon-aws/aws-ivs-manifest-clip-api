import json
import boto3
from datetime import datetime
from boto3.dynamodb.conditions import Key, Attr
import os


print('Loading function')
DB_TABLE_NAME = os.environ['DYNAMO_DB_TABLE_NAME'] 
CLOUDFRONT_URL_FOR_S3 = os.environ['CLOUDFRONT_URL_FOR_S3'] 
TARGET_LAMBDA_FUNCTION_NAME = os.environ['CLIP_API_LAMBDA_ARN'] 

dynamo_table = boto3.resource('dynamodb').Table(DB_TABLE_NAME)
s3 = boto3.client('s3')

def time_difference_in_seconds(time1, time2):
    # Parse the time strings into datetime objects
    time1_dt = datetime.fromisoformat(time1.replace("Z", "+00:00"))
    time2_dt = datetime.fromisoformat(time2.replace("Z", "+00:00"))
    
    # Calculate the time difference
    time_diff = time2_dt - time1_dt
    
    # Return the time difference in seconds
    return time_diff.total_seconds()
    
def invoke_clip_api(payload):
    # Initialize the Lambda client
    lambda_client = boto3.client('lambda')

    # Define the target Lambda function name and payload
    
    target_payload = {
        "body": json.dumps(payload)
    }
    # Invoke the target Lambda function
    response = lambda_client.invoke(
        FunctionName=TARGET_LAMBDA_FUNCTION_NAME,
        InvocationType='RequestResponse',  # Use 'Event' for asynchronous invocation
        Payload=json.dumps(target_payload)
    )

    # Handle the response
    if response['StatusCode'] == 200:
        response_payload = json.loads(response['Payload'].read())
        return response_payload
    else:
        return {
            'statusCode': 500,
            'body': 'Error invoking the target Lambda function',
            'response': response_payload
        }


    
def lambda_handler(event, context):
    try:
        # TODO implement
        body = json.loads(event['body'])
        print("Body: {}".format(body))
        
        channel_arn = body['channel_arn']
        start_time = body['start_time']
        end_time = body['end_time']
        
        duration = time_difference_in_seconds(start_time, end_time)
        print('duration = {}'.format(duration))
        
        res = dynamo_table.query(
            KeyConditionExpression=Key('channel_arn').eq(channel_arn),
            FilterExpression=(
                # 1. recording_start_time is less or equal to start_time and end_time
                (Attr('recording_start_time').ne(None)) &
                (Attr('recording_start_time').lte(start_time)) &
                (Attr('recording_start_time').lte(end_time)) &
                (
                    # 2. recording_end_time is greater or equal to start_time and end_time
                    (
                        (Attr('recording_end_time').gte(start_time)) &
                        (Attr('recording_end_time').gte(end_time))
                    ) |
                    # 3. recording_end_time can be None
                    (Attr('recording_end_time').eq(None))
                )
            )
        )
        
        print("Items: {}".format(res['Items']))
        
        
        if len(res['Items']) <= 0 :
            return {
                'statusCode': 400,
                'body': 'Item Not Found'
            }
        
        if len(res['Items']) > 1 :
            return {
                'statusCode': 400,
                'body': 'TODO Need handling'
            }
        
        # handle the ivs recording
        ivs_recording = res['Items'][0]
        
        # Set the bucket name and prefix path
        bucket_name = ivs_recording['recording_s3_bucket_name']
        prefix_path = ivs_recording['recording_s3_key_prefix']
        file_key = f'{prefix_path}/events/recording-started.json'
        
        # Read the JSON file from the S3 bucket
        response = s3.get_object(Bucket=bucket_name, Key=file_key)
        file_content = response['Body'].read().decode('utf-8')
        data = json.loads(file_content)
        
        # Extract the required data
        recording_started_at = data['recording_started_at']
        hls_path = data['media']['hls']['path']
        hls_playlist = data['media']['hls']['playlist']
        full_hls_path = f"{prefix_path}/{hls_path}/{hls_playlist}"
        master_url = f"{CLOUDFRONT_URL_FOR_S3}/{full_hls_path}"
        
        # Check if byte_range_playlist exists in media.hls
        byte_range_playlist_exists = 'byte_range_playlist' in data['media']['hls'] and data['media']['hls']['byte_range_playlist'] is not None
        
        target_start_time_in_sec = time_difference_in_seconds(recording_started_at, start_time)
        
        # Print the extracted data
        print(f"Recording started at: {recording_started_at}")
        print(f"In seconds at: {target_start_time_in_sec}")
        print(f"Full HLS path: {full_hls_path}")
        print(f"master_url: {master_url}")
        print(f"byte_range_playlist_exists: {byte_range_playlist_exists}")
        
        payload = {
            "start_time": target_start_time_in_sec,
            "end_time": target_start_time_in_sec + duration,
            "master_url": master_url,
            "byte_range":byte_range_playlist_exists
        }
        print("payload: {}".format(payload) )
        
        if ('invoke_clip_api' not in body or  body['invoke_clip_api'] != True):
            return {
                'statusCode': 200,
                'body': json.dumps({
                    "inputs" : payload
                })
            }
        else:
            ret = invoke_clip_api(payload)
            return {
                'statusCode': ret['statusCode'],
                'headers': ret['headers'],
                'body': json.dumps({
                    "inputs" : payload,
                    "clip" : json.loads(ret['body'])
                })
            }
            
        
        
        
    except Exception as e:
        print(e)
        return {
            'statusCode': 400,
            'body': json.dumps('Error : {}'.format(e))
        }
    