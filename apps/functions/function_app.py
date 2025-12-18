"""Azure Functions App - Python v2 Programming Model with Isolated Worker.

This module defines Azure Functions using the v2 programming model with decorator-based
function definitions. The isolated worker process provides better performance and isolation.
"""

import json
import logging
from datetime import datetime

import azure.functions as func

# Create the function app instance
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.route(route="http_trigger", methods=["GET", "POST"])
def http_trigger(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP trigger function example.
    
    This function demonstrates basic HTTP trigger functionality with GET and POST support.
    
    Example:
        GET /api/http_trigger?name=Azure
        POST /api/http_trigger with JSON body: {"name": "Azure"}
    
    Args:
        req: The HTTP request object containing parameters and body
        
    Returns:
        HTTP response with JSON content
    """
    logging.info("HTTP trigger function processing a request.")

    # Try to get name from query parameters
    name = req.params.get("name")
    
    # If not in query params, try request body
    if not name:
        try:
            req_body = req.get_json()
            name = req_body.get("name")
        except (ValueError, AttributeError):
            pass

    if name:
        response_data = {
            "message": f"Hello, {name}! This HTTP triggered function executed successfully.",
            "timestamp": datetime.utcnow().isoformat(),
        }
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=200,
            mimetype="application/json",
        )
    response_data = {
        "message": "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
        "timestamp": datetime.utcnow().isoformat(),
    }
    return func.HttpResponse(
        json.dumps(response_data),
        status_code=200,
        mimetype="application/json",
    )


@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint.
    
    Returns:
        HTTP 200 response indicating the function app is healthy
    """
    logging.info("Health check endpoint called.")
    
    health_data = {
        "status": "healthy",
        "service": "Azure Functions",
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    return func.HttpResponse(
        json.dumps(health_data),
        status_code=200,
        mimetype="application/json",
    )


@app.route(route="echo", methods=["POST"])
def echo(req: func.HttpRequest) -> func.HttpResponse:
    """Echo endpoint that returns the posted data.
    
    Args:
        req: The HTTP request object
        
    Returns:
        HTTP response echoing the request data
    """
    logging.info("Echo function processing request.")
    
    try:
        req_body = req.get_json()
        response_data = {
            "echo": req_body,
            "timestamp": datetime.utcnow().isoformat(),
            "content_type": req.headers.get("Content-Type"),
        }
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=200,
            mimetype="application/json",
        )
    except (ValueError, AttributeError):
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON in request body"}),
            status_code=400,
            mimetype="application/json",
        )
