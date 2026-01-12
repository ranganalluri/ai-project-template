"""Quick test to verify schema format matches expected structure."""
import sys
import json
sys.path.insert(0, 'apps/common-py/src')

from common.schemas.invoice_schema import Invoice

# Get the schema
schema_def = Invoice.get_json_schema_definition()
schema = schema_def["schema"]

# Print the schema structure
print("Schema keys:", list(schema.keys()))
print("\nSchema type:", schema.get("type"))
print("Has required:", "required" in schema)
if "required" in schema:
    print("Required fields:", schema["required"][:5], "...")  # First 5

# Check a sample property (customer_name)
if "properties" in schema and "customer_name" in schema["properties"]:
    customer_name = schema["properties"]["customer_name"]
    print("\n=== customer_name property ===")
    print("Type:", customer_name.get("type"))
    print("Has additionalProperties:", "additionalProperties" in customer_name)
    print("Has required:", "required" in customer_name)
    if "required" in customer_name:
        print("Required fields:", customer_name["required"])
    if "properties" in customer_name:
        print("Properties:", list(customer_name["properties"].keys()))
        if "value" in customer_name["properties"]:
            print("Value type:", customer_name["properties"]["value"].get("type"))
        if "spans" in customer_name["properties"]:
            spans = customer_name["properties"]["spans"]
            print("Spans type:", spans.get("type"))
            if "items" in spans:
                items = spans["items"]
                print("Spans items type:", items.get("type"))
                print("Spans items has required:", "required" in items)
                if "required" in items:
                    print("Spans items required:", items["required"])

# Print full schema for one property as JSON
print("\n=== Full customer_name schema (pretty) ===")
if "properties" in schema and "customer_name" in schema["properties"]:
    print(json.dumps(schema["properties"]["customer_name"], indent=2))

