from models.dynamo import query_gsi
from utils.responses import success, error


def handler(event, context):
    """AWS Lambda handler for GET /drones/{drone_id}/inspections."""
    try:
        # Extract path parameters
        path_parameters = event.get("pathParameters") or {}
        drone_id = path_parameters.get("drone_id")

        if not drone_id:
            return error(
                message="drone_id parameter is missing from the request path",
                status_code=400,
                code="MISSING_PATH_PARAMETER",
            )

        # Retrieve matching records from GSI2
        items = query_gsi(
            index_name="GSI2-DroneInspections",
            pk_name="GSI2PK",
            pk_value=f"DRONE#{drone_id}",
        )

        # Clean output key names for client convenience
        inspections = []
        for item in items:
            inspections.append({
                "inspection_id": item.get("inspection_id"),
                "warehouse_id": item.get("warehouse_id"),
                "status": item.get("status"),
                "created_at": item.get("created_at"),
            })

        return success(
            data={
                "drone_id": drone_id,
                "inspections": inspections,
            }
        )

    except Exception as e:
        return error(
            message=f"An unexpected internal error occurred: {str(e)}",
            status_code=500,
            code="INTERNAL_ERROR",
        )