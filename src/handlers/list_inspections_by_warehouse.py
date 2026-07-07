from models.dynamo import query_gsi
from utils.responses import success, error


def handler(event, context):
    """AWS Lambda handler for GET /warehouses/{warehouse_id}/inspections."""
    try:
        # Extract path parameters
        path_parameters = event.get("pathParameters") or {}
        warehouse_id = path_parameters.get("warehouse_id")

        if not warehouse_id:
            return error(
                message="warehouse_id parameter is missing from the request path",
                status_code=400,
                code="MISSING_PATH_PARAMETER",
            )

        # Retrieve matching records from GSI1
        items = query_gsi(
            index_name="GSI1-WarehouseInspections",
            pk_name="GSI1PK",
            pk_value=f"WAREHOUSE#{warehouse_id}",
        )

        # Clean output key names for client convenience
        inspections = []
        for item in items:
            inspections.append({
                "inspection_id": item.get("inspection_id"),
                "drone_id": item.get("drone_id"),
                "status": item.get("status"),
                "created_at": item.get("created_at"),
            })

        return success(
            data={
                "warehouse_id": warehouse_id,
                "inspections": inspections,
            }
        )

    except Exception as e:
        return error(
            message=f"An unexpected internal error occurred: {str(e)}",
            status_code=500,
            code="INTERNAL_ERROR",
        )