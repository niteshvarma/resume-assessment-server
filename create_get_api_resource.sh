#!/bin/bash

# Check if correct number of arguments are provided
if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <resource-name> <stage-name>"
  exit 1
fi

# Define variables from command line parameters
RESOURCE_NAME=$1
STAGE_NAME=$2
EC2_IP="3.238.171.94"
PORT="80"

# Define API Gateway Name
API_GATEWAY_NAME="recruitr-api"

# Get the API ID dynamically based on the API Gateway name
API_ID=$(aws apigatewayv2 get-apis --query "Items[?Name=='$API_GATEWAY_NAME'].ApiId" --output text)

# Ensure we got the API ID
if [ "$API_ID" == "None" ]; then
  echo "Error: API Gateway '$API_GATEWAY_NAME' not found."
  exit 1
fi

echo "Using API Gateway with API ID: $API_ID"

# Create /resource route for GET
echo "Creating $RESOURCE_NAME GET resource..."
CREATE_ROUTE_RESULT=$(aws apigatewayv2 create-route --api-id "$API_ID" --route-key "GET /$RESOURCE_NAME")

# Exit if route creation fails
if [ $? -ne 0 ]; then
  echo "Error: Failed to create GET route for $RESOURCE_NAME"
  exit 1
fi

# Extract Route ID
ROUTE_ID=$(echo "$CREATE_ROUTE_RESULT" | jq -r '.RouteId')

echo "Route ID for GET /$RESOURCE_NAME: $ROUTE_ID"

# Create HTTP Proxy integration for the GET resource
echo "Creating HTTP Proxy integration for GET /$RESOURCE_NAME..."
CREATE_INTEGRATION_RESULT=$(aws apigatewayv2 create-integration --api-id "$API_ID" --integration-type HTTP_PROXY \
  --integration-method GET --integration-uri "http://$EC2_IP:$PORT/$RESOURCE_NAME" --payload-format-version "1.0")

# Exit if integration creation fails
if [ $? -ne 0 ]; then
  echo "Error: Failed to create integration for GET /$RESOURCE_NAME"
  exit 1
fi

# Extract Integration ID
INTEGRATION_ID=$(echo "$CREATE_INTEGRATION_RESULT" | jq -r '.IntegrationId')

# Set integration target for the route
echo "Setting integration target for GET /$RESOURCE_NAME route..."
aws apigatewayv2 update-route --api-id "$API_ID" --route-id "$ROUTE_ID" --target "integrations/$INTEGRATION_ID"

# Exit if route update fails
if [ $? -ne 0 ]; then
  echo "Error: Failed to update route for GET /$RESOURCE_NAME"
  exit 1
fi

# Set up CORS for the resource
echo "Setting up CORS response for OPTIONS method..."

OPTIONS_ROUTE_RESULT=$(aws apigatewayv2 create-route --api-id "$API_ID" --route-key "OPTIONS /$RESOURCE_NAME")

# Exit if OPTIONS route creation fails
if [ $? -ne 0 ]; then
  echo "Error: Failed to create OPTIONS route for $RESOURCE_NAME"
  exit 1
fi

OPTIONS_ROUTE_ID=$(echo "$OPTIONS_ROUTE_RESULT" | jq -r '.RouteId')

# Set up response parameters with CORS
aws apigatewayv2 create-route-response --api-id "$API_ID" --route-id "$OPTIONS_ROUTE_ID" --route-response-key "default" \
  --response-parameters '{"method.response.header.Access-Control-Allow-Origin": {"Required": "*"}, 
                          "method.response.header.Access-Control-Allow-Headers": {"Required": "content-type, authorization"}, 
                          "method.response.header.Access-Control-Allow-Methods": {"Required": "GET,OPTIONS"}}'

# Exit if CORS setup fails
if [ $? -ne 0 ]; then
  echo "Error: Failed to set up CORS for GET /$RESOURCE_NAME"
  exit 1
fi

echo "CORS setup complete for GET /$RESOURCE_NAME."

# Deploy API
echo "Deploying API..."
aws apigatewayv2 create-deployment --api-id "$API_ID" --stage-name "$STAGE_NAME"

# Exit if deployment fails
if [ $? -ne 0 ]; then
  echo "Error: Failed to deploy the API."
  exit 1
fi

echo "Deployment complete."
