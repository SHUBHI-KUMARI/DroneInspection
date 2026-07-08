import os
import boto3
from boto3.dynamodb.conditions import Key

# Initialize the DynamoDB resource client
dynamodb = boto3.resource("dynamodb")
table_name = os.environ.get("TABLE_NAME", "InspectionSystem")
table = dynamodb.Table(table_name)


def put_item(item: dict) -> None:
    """Writes a single dictionary item to the DynamoDB table."""
    table.put_item(Item=item)


def get_item(pk: str, sk: str) -> dict:
    """Retrieves a single item based on its exact PK and SK keys.
    
    Returns None if the item is not found.
    """
    response = table.get_item(Key={"PK": pk, "SK": sk})
    return response.get("Item")


def query_by_pk_prefix(pk: str, sk_prefix: str) -> list:
    """Queries for items sharing a common Partition Key (PK) 
    where the Sort Key (SK) begins with a given prefix string.
    """
    response = table.query(
        KeyConditionExpression=Key("PK").eq(pk) & Key("SK").begins_with(sk_prefix)
    )
    return response.get("Items", [])


def query_gsi(index_name: str, pk_name: str, pk_value: str) -> list:
    """Queries a specific Global Secondary Index (GSI) using the index's
    respective partition key name and matching value.
    """
    response = table.query(
        IndexName=index_name,
        KeyConditionExpression=Key(pk_name).eq(pk_value),
    )
    return response.get("Items", [])