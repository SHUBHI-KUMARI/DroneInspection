import json


def success(data: dict, status_code: int = 200) -> dict:
    """Formats a successful Lambda proxy response containing the result payload.
    
    Args:
        data: The output payload dictionary to include in the body.
        status_code: The HTTP status code (defaults to 200).
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS"
        },
        "body": json.dumps({
            "success": True,
            "data": data
        }),
    }


def error(message: str, status_code: int = 400, code: str = "BAD_REQUEST") -> dict:
    """Formats a failure/error Lambda proxy response with details.
    
    Args:
        message: Descriptive error message explaining what failed.
        status_code: Corresponding HTTP status code (defaults to 400).
        code: Machine-readable specific error classification code.
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS"
        },
        "body": json.dumps({
            "success": False,
            "error": {
                "code": code,
                "message": message
            }
        }),
    }