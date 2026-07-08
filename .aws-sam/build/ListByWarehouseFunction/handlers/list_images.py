from models.dynamo import query_by_pk_prefix
from utils.responses import success, error


def handler(event, context):
    """AWS Lambda handler for GET /inspections/{inspection_id}/images."""
    try:
        # Extract path parameters
        path_parameters = event.get("pathParameters") or {}
        inspection_id = path_parameters.get("inspection_id")

        if not inspection_id:
            return error(
                message="inspection_id parameter is missing from the request path",
                status_code=400,
                code="MISSING_PATH_PARAMETER",
            )

        # Query all items sharing the inspection partition key prefixing IMAGE#
        items = query_by_pk_prefix(
            pk=f"INSPECTION#{inspection_id}",
            sk_prefix="IMAGE#",
        )

        # Format details into clean dictionary entries for client retrieval
        images = []
        for item in items:
            images.append({
                "image_id": item.get("image_id"),
                "s3_key": item.get("s3_key"),
                "content_type": item.get("content_type"),
                "uploaded_at": item.get("uploaded_at"),
            })

        return success(
            data={
                "inspection_id": inspection_id,
                "images": images,
            }
        )

    except Exception as e:
        return error(
            message=f"An unexpected internal error occurred: {str(e)}",
            status_code=500,
            code="INTERNAL_ERROR",
        )