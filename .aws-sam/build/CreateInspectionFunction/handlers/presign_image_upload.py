import json
import os
import uuid
from datetime import datetime, timezone
import boto3
from models.dynamo import put_item
from utils.responses import success, error

# Initialize S3 client outside the handler for reuse across invocations
s3_client = boto3.client("s3")
bucket_name = os.environ.get("BUCKET_NAME")


def handler(event, context):
    """AWS Lambda handler for POST /inspections/{inspection_id}/images/presign."""
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

        # Parse request body (optional content_type default to image/jpeg)
        body = json.loads(event.get("body") or "{}")
        content_type = body.get("content_type", "image/jpeg")

        # Basic type validation
        allowed_types = ["image/jpeg", "image/png", "image/webp"]
        if content_type not in allowed_types:
            return error(
                message=f"Unsupported image content_type. Allowed: {', '.join(allowed_types)}",
                status_code=400,
                code="UNSUPPORTED_MEDIA_TYPE",
            )

        # Generate unique image parameters
        image_id = str(uuid.uuid4())
        extension = content_type.split("/")[-1]
        s3_key = f"inspections/{inspection_id}/{image_id}.{extension}"
        expires_in = 300  # 5 minutes link expiration duration

        # Generate the S3 PUT pre-signed URL
        upload_url = s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": bucket_name,
                "Key": s3_key,
                "ContentType": content_type,
            },
            ExpiresIn=expires_in,
        )

        # Prepare DynamoDB Metadata Record
        metadata = {
            "PK": f"INSPECTION#{inspection_id}",
            "SK": f"IMAGE#{image_id}",
            "image_id": image_id,
            "inspection_id": inspection_id,
            "s3_key": s3_key,
            "content_type": content_type,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }

        # Save metadata record in DynamoDB (optimistic write design)
        put_item(metadata)

        return success(
            data={
                "image_id": image_id,
                "upload_url": upload_url,
                "s3_key": s3_key,
                "expires_in_seconds": expires_in,
            }
        )

    except json.JSONDecodeError:
        return error(
            message="Invalid JSON payload provided in request body",
            status_code=400,
            code="INVALID_JSON",
        )
    except Exception as e:
        return error(
            message=f"An unexpected internal error occurred: {str(e)}",
            status_code=500,
            code="INTERNAL_ERROR",
        )