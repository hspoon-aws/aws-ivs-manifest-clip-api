# Clip API Wrapper

Clip API Wrapper is a serverless application built on top of the Amazon IVS Clip Manifest Standalone API. It extends the functionality by allowing users to input start and end times in UTC time string format instead of seconds. The project consists of two AWS Lambda functions, `ivs-recording-state-change-handler` and `clip-api-wrapper`, which work together to provide this functionality.

## Overview

1. The `ivs-recording-state-change-handler` listens for IVS recording state change events from Amazon EventBridge and stores metadata in an Amazon DynamoDB table.
2. The `clip-api-wrapper` is an API-triggered Lambda function that:
   - Accepts the IVS channel ARN, start time, and end time in UTC time string format.
   - Queries metadata from the DynamoDB table to get the IVS recording path in Amazon S3.
   - Retrieves the recording start time from the S3 events/record-started.json file to calculate the video timestamp in seconds from the UTC time string.
   - Passes the calculated parameters to the original Amazon IVS Clip Manifest Standalone API using `Lambda.invoke()` and returns the IVS Clip Manifest details to the API caller.

## Prerequisites

Before you can deploy the Clip API Wrapper SAM project, you must first install the "standalone-api" SAM template in your AWS account.

### Installing the Standalone API

Follow these steps to install the Standalone API:

1. Navigate to the Standalone API project directory:
    ``` 
    cd ../standalone-api
    ```

2. Deploy the Standalone API using the AWS SAM CLI:

    ```
    sam build
    sam deploy --guided
    ```

- During the guided deployment, you will be prompted for various configuration options. Provide the necessary information to configure the Standalone API for your AWS account.
- Once the deployment is complete, note the output values for various resources, such as the API Gateway URL, Lambda function ARN, etc. You may need them for configuring the Clip API Wrapper project.

## Deploying the Clip API Wrapper

After installing the Standalone API, you can proceed to deploy the Clip API Wrapper SAM project. Ensure that you have the necessary resources, such as Amazon IVS channels, recordings, and other settings, in place before you begin.

1. Navigate to the Clip API Wrapper project directory:
    ```
    cd ../clip-api-wrapper
    ```
2. Deploy the Clip API Wrapper using the AWS SAM CLI:
    ```
    sam build
    sam deploy --guided
    ```

- During the guided deployment, you will be prompted for various configuration options. Provide the necessary information to configure the Clip API Wrapper for your AWS account, such as the Lambda function ARNs from the Standalone API project.
- Once the deployment is complete, note the output values for various resources, such as the API Gateway URL for the `clip-api-wrapper` function.

## Usage

To use the Clip API Wrapper, make an API request to the endpoint URL provided in the deployment output, passing the required parameters (IVS channel ARN, start time, and end time in UTC time string format).

Here's a sample request using cURL:

```
curl -X POST https://your-api-gateway-url.amazonaws.com/default/clip-api-wrapper \
  -H "Content-Type: application/json" \
  -d '{
        "channelArn": "arn:aws:ivs:us-west-2:123456789012:channel/abcdef123456",
        "startTime": "2023-01-01T00:00:00Z",
        "endTime": "2023-01-01T00:01:00Z"
        "invoke_clip_api": true
      }'
```

Replace `your-api-gateway-url` with the API Gateway URL from the deployment output, and provide the appropriate values for `channelArn`, `startTime`, and `endTime`. `invoke_clip_api` indicates whether the API return the generated clip manifest directly or not. 

The API will return the IVS Clip Manifest details in `clip.master_url`, which can be used to play the clip using an IVS player or download the clip using a compatible media player or tool.

Sample output:
```
{
    "inputs": {
        "start_time": 184.0,
        "end_time": 244.0,
        "master_url": "https://distribution.cloudfront.net/ivs/v1/account_id/recording_id/2023/4/30/15/5/session_id/media/hls/master.m3u8",
        "byte_range": true
    },
    "clip": [
        {
            "execution": 1682872435820,
            "path": "/ivs/v1/account_id/recording_id/2023/4/30/15/5/rcwkb25xBAkP/media/hls",
            "bucket": "standalone-api-generated-bucket",
            "clip_master": "ustandalone-api-generated-bucket/ivs/v1/account_id/recording_id/2023/4/30/15/5/session_id/media/hls/1682872435820_clip_master.m3u8",
            "master_url": "https://distribution.cloudfront.net/ivs/v1/account_id/recording_id/2023/4/30/15/5/session_id/media/hls/1682872435820_clip_master.m3u8"
        }
    ]
}
```

## Support and Contributions

If you have any questions, issues, or feature requests, please open an issue in the project's GitHub repository. Contributions are also welcome. Pleasefollow the repository's contribution guidelines when submitting pull requests.

## License

This project is released under the [MIT License](LICENSE). Please see the [LICENSE](LICENSE) file for details.