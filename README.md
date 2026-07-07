# Drone Inspection Backend

A serverless backend for managing drone inspections across warehouses — built on AWS Lambda, API Gateway, DynamoDB, and S3.

**GitHub Repository:** [https://github.com/SHUBHI-KUMARI/DroneInspection](https://github.com/SHUBHI-KUMARI/DroneInspection)


## Overview

This service tracks four related entities and exposes them through a REST API:

- **Warehouse** → **Drones** (one-to-many)
- **Warehouse** → **Inspections** (one-to-many)
- **Drone** → **Inspections** (one-to-many)
- **Inspection** → **Images** (one-to-many)

The entire stack is defined as infrastructure-as-code (AWS SAM) and deployed with a single command. All Lambda functions run under least-privilege IAM roles with no hardcoded credentials.

## Architecture

### System Diagram

```text
                               ┌───────────────┐
                               │  API Gateway  │
                               └───────┬───────┘
                                       │
      ┌──────────────────┬─────────────┴────────────┬──────────────────┐
      ▼                  ▼                          ▼                  ▼
┌────────────┐   ┌────────────────┐           ┌────────────┐     ┌────────────┐
│   create_  │   │      list_     │           │  presign_  │     │    list_   │
│ inspection │   │  inspections   │           │    image_  │     │   images   │
│  (Lambda)  │   │    (Lambda)    │           │   upload   │     │  (Lambda)  │
│            │   │                │           │  (Lambda)  │     │            │
└─────┬──────┘   └───────┬────────┘           └─────┬──────┘     └─────┬──────┘
      │                  │                          │                  │
      └─────────┬────────┴──────────────────────────┼──────────────────┘
                ▼                                   │
┌───────────────────────────────┐                   │
│      DynamoDB: Table          │                   │
│     InspectionSystem          │                   │
│ (Single-Table + 2 GSIs)       │                   │
└───────────────────────────────┘                   ▼
                                     ┌─────────────────────────────┐
                                     │          S3 Bucket          │
                                     │        (Image Files)        │
                                     └──────────────▲──────────────┘
                                                    │
                                                    │ (Direct PUT upload via
                                                    │  pre-signed URL)
                                                    │
                                             ┌──────┴──────┐
                                             │   Client    │
                                             └─────────────┘
```

### Visual Flowchart

![System Architecture Flowchart](https://mermaid.ink/img/Z3JhcGggVEQKICAgIEFQSUdXW0FQSSBHYXRld2F5XQogICAgQVBJR1cgLS0+IENyZWF0ZVtjcmVhdGVfaW5zcGVjdGlvbiBMYW1iZGFdCiAgICBBUElHVyAtLT4gTGlzdFtsaXN0X2luc3BlY3Rpb25zIExhbWJkYV0KICAgIEFQSUdXIC0tPiBQcmVzaWduW3ByZXNpZ25faW1hZ2VfdXBsb2FkIExhbWJkYV0KICAgIEFQSUdXIC0tPiBMaXN0SW1nW2xpc3RfaW1hZ2VzIExhbWJkYV0KICAgIENyZWF0ZSAtLT4gREJbKER5bmFtb0RCKV0KICAgIExpc3QgLS0+IERCCiAgICBQcmVzaWduIC0tPiBEQgogICAgTGlzdEltZyAtLT4gREIKICAgIFByZXNpZ24gLS4tPiBTM1soUzMgQnVja2V0KV0KICAgIENsaWVudFtDbGllbnRdIC0tPnwxLiBSZXF1ZXN0IFVSTHwgUHJlc2lnbgogICAgQ2xpZW50IC0tPnwyLiBEaXJlY3QgUFVUfCBTMw==)

**Image upload flow:**


1. Client requests a pre-signed URL via `POST /inspections/{id}/images/presign`.
2. Lambda generates a time-limited S3 `PUT` URL (5-minute expiry) and writes an image metadata record to DynamoDB.
3. Client uploads the file directly to S3 using that URL. Lambda and API Gateway are not part of the file transfer — this satisfies the requirement to avoid routing uploads through Lambda.

## Tech Stack

| Component | Purpose |
| :--- | :--- |
| **Python 3.9** | Lambda runtime |
| **AWS Lambda** | One function per API operation (5 total) |
| **API Gateway** | REST API routing |
| **DynamoDB** | Single-table storage for all entities and associations |
| **S3** | Image storage, accessed via pre-signed URLs |
| **IAM** | Per-function execution roles, scoped to minimum required resources |
| **AWS SAM** | Infrastructure defined in `template.yaml`, deployed via `sam deploy` |

---

## DynamoDB Design

### Table: `InspectionSystem`

| PK | SK | Represents |
| :--- | :--- | :--- |
| `WAREHOUSE#<id>` | `METADATA` | Warehouse record |
| `WAREHOUSE#<id>` | `DRONE#<id>` | Drone assigned to a warehouse |
| `DRONE#<id>` | `METADATA` | Drone record |
| `INSPECTION#<id>` | `METADATA` | Inspection record |
| `INSPECTION#<id>` | `IMAGE#<id>` | Image belonging to an inspection |

### Global Secondary Indexes

| Index | Partition Key | Sort Key | Supports |
| :--- | :--- | :--- | :--- |
| `GSI1-WarehouseInspections` | `GSI1PK = WAREHOUSE#<warehouse_id>` | `GSI1SK = INSPECTION#<created_at>#<id>` | List inspections by warehouse |
| `GSI2-DroneInspections` | `GSI2PK = DRONE#<drone_id>` | `GSI2SK = INSPECTION#<created_at>#<id>` | List inspections by drone |

### Design rationale

DynamoDB does not support joins or efficient full-table scans, so queries need to be designed around known access patterns rather than normalized entity structure. This service uses a single table with generic `PK`/`SK` attributes and two GSIs, so every inspection is written once with both index keys already attached. Each required read (list by warehouse, list by drone, list images for inspection) resolves to a single indexed `Query` call, with no application-side joins or filtering.

The trade-off is a marginally more involved write path — one item carries three sets of key attributes instead of one — in exchange for constant-time, indexed reads. Given inspections are created infrequently relative to how often they're listed and viewed, this favors read performance.

## Access Patterns

| # | Pattern | Implementation |
| :--- | :--- | :--- |
| **1** | Create an inspection for a warehouse and drone | `PutItem`, writing `PK/SK` and both GSI key sets in one call |
| **2** | List inspections by warehouse | `Query` on `GSI1-WarehouseInspections` |
| **3** | List inspections by drone | `Query` on `GSI2-DroneInspections` |
| **4** | Upload an inspection image | Lambda issues an S3 pre-signed `PUT` URL; client uploads directly; Lambda records an `IMAGE#` item under the inspection's `PK` |
| **5** | List images for an inspection | `Query` where `PK = INSPECTION#<id>` and `SK begins_with IMAGE#` |
| **6** | List drones for a warehouse (supporting pattern) | `Query` where `PK = WAREHOUSE#<id>` and `SK begins_with DRONE#` |

---

## API Reference

### `POST /inspections`

Create an inspection for a given warehouse and drone.

#### Request
```json
{
  "warehouse_id": "wh-001",
  "drone_id": "dr-001"
}
```

#### Response — 201 Created
```json
{
  "success": true,
  "data": {
    "inspection_id": "b2a1e6f0-...",
    "warehouse_id": "wh-001",
    "drone_id": "dr-001",
    "status": "PENDING",
    "created_at": "2026-07-07T10:15:00+00:00"
  }
}
```

#### Response — 400 Bad Request
```json
{
  "success": false,
  "error": {
    "code": "MISSING_FIELDS",
    "message": "warehouse_id and drone_id are both required"
  }
}
```

---

### `GET /warehouses/{warehouse_id}/inspections`

Returns all inspections recorded for a given warehouse.

#### Response — 200 OK
```json
{
  "success": true,
  "data": {
    "warehouse_id": "wh-001",
    "inspections": [
      {
        "inspection_id": "b2a1e6f0-...",
        "drone_id": "dr-001",
        "status": "PENDING",
        "created_at": "2026-07-07T10:15:00+00:00"
      }
    ]
  }
}
```

---

### `GET /drones/{drone_id}/inspections`

Returns all inspections carried out by a given drone.

#### Response — 200 OK
```json
{
  "success": true,
  "data": {
    "drone_id": "dr-001",
    "inspections": [
      {
        "inspection_id": "b2a1e6f0-...",
        "warehouse_id": "wh-001",
        "status": "PENDING",
        "created_at": "2026-07-07T10:15:00+00:00"
      }
    ]
  }
}
```

---

### `POST /inspections/{inspection_id}/images/presign`

Generates a pre-signed S3 URL for uploading an image to the given inspection.

#### Request
```json
{
  "content_type": "image/jpeg"
}
```

#### Response — 200 OK
```json
{
  "success": true,
  "data": {
    "image_id": "c9d2f1a0-...",
    "upload_url": "https://drone-inspection-images-xxxx.s3.amazonaws.com/inspections/.../c9d2f1a0-....jpg?X-Amz-...",
    "s3_key": "inspections/b2a1e6f0-.../c9d2f1a0-....jpg",
    "expires_in_seconds": 300
  }
}
```

#### Client upload command
Client then uploads directly:
```bash
curl -X PUT "<upload_url>" -H "Content-Type: image/jpeg" --upload-file ./photo.jpg
```

---

### `GET /inspections/{inspection_id}/images`

Returns all images uploaded for a given inspection.

#### Response — 200 OK
```json
{
  "success": true,
  "data": {
    "inspection_id": "b2a1e6f0-...",
    "images": [
      {
        "image_id": "c9d2f1a0-...",
        "s3_key": "inspections/b2a1e6f0-.../c9d2f1a0-....jpg",
        "content_type": "image/jpeg",
        "uploaded_at": "2026-07-07T10:16:40+00:00"
      }
    ]
  }
}
```

---

## Error Handling

All responses follow a consistent shape:

```json
{
  "success": true,
  "data": { ... }
}
```
```json
{
  "success": false,
  "error": {
    "code": "...",
    "message": "..."
  }
}
```

| Status | Condition |
| :--- | :--- |
| **200** | Successful read |
| **201** | Successful create |
| **400** | Invalid or missing input |
| **404** | Resource not found |
| **500** | Unhandled server error (caught; no raw stack traces returned) |

---

## IAM & Security

- Each Lambda function has its own execution role, generated from the `Policies:` block in `template.yaml`.
- `create_inspection`: `DynamoDBCrudPolicy` scoped to the `InspectionSystem` table.
- `list_inspections_by_warehouse`, `list_inspections_by_drone`, `list_images`: read-only `DynamoDBReadPolicy`, scoped to the same table.
- `presign_image_upload`: `S3CrudPolicy` scoped to the image bucket, plus `DynamoDBCrudPolicy` scoped to the table.
- No AWS credentials are present in code or configuration. Lambda receives temporary credentials from its execution role at runtime.

---

## Deployment

**Prerequisites:** AWS CLI, AWS SAM CLI, Python 3.9+, an AWS account.

```bash
pip install -r requirements.txt
sam build
sam deploy --guided     # first deployment
sam deploy               # subsequent deployments
```

SAM prints the API Gateway base URL on completion.

---

## Testing

```bash
curl -X POST https://<api-url>/inspections \
  -H "Content-Type: application/json" \
  -d '{"warehouse_id": "wh-001", "drone_id": "dr-001"}'

curl https://<api-url>/warehouses/wh-001/inspections

curl https://<api-url>/drones/dr-001/inspections

curl -X POST https://<api-url>/inspections/<inspection_id>/images/presign \
  -H "Content-Type: application/json" \
  -d '{"content_type": "image/jpeg"}'

curl -X PUT "<upload_url>" -H "Content-Type: image/jpeg" --upload-file ./test-image.jpg

curl https://<api-url>/inspections/<inspection_id>/images
```

---

## Project Structure

```text
drone-inspection-backend/
├── README.md
├── template.yaml
├── requirements.txt
├── src/
│   ├── handlers/
│   │   ├── create_inspection.py
│   │   ├── list_inspections_by_warehouse.py
│   │   ├── list_inspections_by_drone.py
│   │   ├── presign_image_upload.py
│   │   └── list_images.py
│   ├── models/
│   │   └── dynamo.py
│   └── utils/
│       └── responses.py
└── tests/
    └── test_handlers.py
```

---

