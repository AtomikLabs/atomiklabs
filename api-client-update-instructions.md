# API Client Update Instructions

The API Gateway is now configured to require an API key for authentication. The API key is provided to the ECS task as an environment variable named `API_KEY`. The API client code needs to be updated to include this API key in the request headers.

## Required Changes

Update the `api_client.py` file to include the API key in the request headers:

```python
# In the _make_request method, add the API key to the headers
headers = {
    "Content-Type": "application/json",
    "User-Agent": "ArxivProcessor/1.0",
    "Host": host,  # Required for SigV4
    "X-Amz-Date": datetime.utcnow().strftime('%Y%m%dT%H%M%SZ'),  # Required for SigV4
    "x-api-key": os.environ.get('API_KEY', '')  # Add the API key header
}
```

This change should be made before the SigV4 signing process, as the API key header needs to be included in the signature.

## Testing

After deploying these changes, the API client should be able to authenticate with the API Gateway using both AWS IAM authentication and the API key.

If you're still seeing "INVALID_API_KEY" errors, check the following:

1. Verify that the API key is correctly set in the ECS task environment variables
2. Verify that the API key is correctly included in the request headers
3. Verify that the API key is correctly associated with the usage plan
4. Verify that the usage plan is correctly associated with the API stage

## Troubleshooting

If you're still having issues, you can try the following:

1. Check the CloudWatch logs for the API Gateway to see if there are any additional error messages
2. Use the AWS CLI to test the API Gateway with the API key:

```bash
aws apigateway test-invoke-method \
  --rest-api-id <api-id> \
  --resource-id <resource-id> \
  --http-method GET \
  --path-with-query-string "/papers?limit=1" \
  --headers '{"x-api-key":"<api-key>"}'
```

Replace `<api-id>`, `<resource-id>`, and `<api-key>` with the appropriate values.
