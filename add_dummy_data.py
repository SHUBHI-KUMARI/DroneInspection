import os
import uuid
import datetime
import boto3
from datetime import timezone

TABLE_NAME = "InspectionSystem"
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table(TABLE_NAME)

def add_dummy_data():
    print(f"Adding dummy data to {TABLE_NAME}...")
    
    # We will generate a few warehouses and drones
    warehouses = [f"wh-00{i}" for i in range(1, 4)]
    drones = [f"dr-00{i}" for i in range(1, 4)]
    
    count = 0
    for wh in warehouses:
        for dr in drones:
            for _ in range(2):
                inspection_id = str(uuid.uuid4())
                created_at = datetime.datetime.now(timezone.utc).isoformat()
                
                # Inspection metadata
                inspection_item = {
                    "PK": f"INSPECTION#{inspection_id}",
                    "SK": "METADATA",
                    "inspection_id": inspection_id,
                    "warehouse_id": wh,
                    "drone_id": dr,
                    "status": "COMPLETED",
                    "created_at": created_at,
                    "GSI1PK": f"WAREHOUSE#{wh}",
                    "GSI1SK": f"INSPECTION#{created_at}#{inspection_id}",
                    "GSI2PK": f"DRONE#{dr}",
                    "GSI2SK": f"INSPECTION#{created_at}#{inspection_id}",
                }
                table.put_item(Item=inspection_item)
                count += 1
                
                # Add images
                for _ in range(3):
                    image_id = str(uuid.uuid4())
                    s3_key = f"inspections/{inspection_id}/{image_id}.jpeg"
                    image_item = {
                        "PK": f"INSPECTION#{inspection_id}",
                        "SK": f"IMAGE#{image_id}",
                        "image_id": image_id,
                        "inspection_id": inspection_id,
                        "s3_key": s3_key,
                        "content_type": "image/jpeg",
                        "uploaded_at": datetime.datetime.now(timezone.utc).isoformat(),
                    }
                    table.put_item(Item=image_item)
                    count += 1

    print(f"Inserted {count} dummy records (inspections and images) into DynamoDB.")

if __name__ == "__main__":
    add_dummy_data()
