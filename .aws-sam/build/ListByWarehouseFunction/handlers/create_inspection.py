import json
import uuid
from datetime import datetime, timezone
from models.dynamo import put_item
from utils.responses import success, error


def handler(event, context):
    """AWS Lambda handler for POST /inspections."""
    try:
        # Parse the JSON request body
        body = json.loads(event.get("body") or "{}")
        warehouse_id = body.get("warehouse_id")
        drone_id = body.get("drone_id")

        # Validate input fields
        if not warehouse_id or not drone_id:
            return error(
                message="warehouse_id and drone_id are both required fields",
                status_code=400,
                code="MISSING_FIELDS",
            )

        # Generate tracking information
        inspection_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        # Build single-table design item with multiple index parameters
        item = {
            "PK": f"INSPECTION#{inspection_id}",
            "SK": "METADATA",
            "inspection_id": inspection_id,
            "warehouse_id": warehouse_id,
            "drone_id": drone_id,
            "status": "PENDING",
            "created_at": created_at,
            # GSI1: Primary index for warehouse inspection lookups
            "GSI1PK": f"WAREHOUSE#{warehouse_id}",
            "GSI1SK": f"INSPECTION#{created_at}#{inspection_id}",
            # GSI2: Primary index for drone inspection lookups
            "GSI2PK": f"DRONE#{drone_id}",
            "GSI2SK": f"INSPECTION#{created_at}#{inspection_id}",
        }

        # Write item to DynamoDB
        put_item(item)

        # Return success with created object info
        return success(
            data={
                "inspection_id": inspection_id,
                "warehouse_id": warehouse_id,
                "drone_id": drone_id,
                "status": "PENDING",
                "created_at": created_at,
            },
            status_code=201,
        )

    except json.JSONDecodeError:
        return error(
            message="Invalid JSON payload provided in request body",
            status_code=400,
            code="INVALID_JSON",
        )
    except Exception as e:
        # Avoid leaking internal system traces, return clean generic error
        return error(
            message=f"An unexpected internal error occurred: {str(e)}",
            status_code=500,
            code="INTERNAL_ERROR",
        )