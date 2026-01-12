from __future__ import annotations
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class Span(BaseModel):
    """Text span with offset and length."""
    offset: int = Field(..., description="Character offset in the document")
    length: int = Field(..., description="Length of the span in characters")


class CitedValue(BaseModel):
    """A value with citation information (flattened structure)."""
    value: Any = Field(..., description="The extracted value")
    spans: list[Span] = Field(default_factory=list, description="Text spans where the value was found")
    quote: Optional[str] = Field(None, description="Quoted text that was extracted")
    reason: Optional[str] = Field(None, description="Reason for extracting this value")


class InvoiceAddress(BaseModel):
    """
    A class representing an address in an invoice.

    Attributes:
        street: Street address
        city: City, e.g. New York
        state: State, e.g. NY
        postal_code: Postal code, e.g. 10001
        country: Country, e.g. USA
        phone: Phone number, e.g. +1-123-456-7890
    """

    street: Optional[CitedValue] = Field(None, description="Street address, e.g. 123 Main St.")
    city: Optional[CitedValue] = Field(None, description="City, e.g. New York")
    state: Optional[CitedValue] = Field(None, description="State, e.g. NY")
    postal_code: Optional[CitedValue] = Field(None, description="Postal code, e.g. 10001")
    country: Optional[CitedValue] = Field(None, description="Country, e.g. USA.")
    phone: Optional[CitedValue] = Field(None, description="Phone number, e.g. +1-123-456-7890.")

    @staticmethod
    def example():
        """
        Creates an empty example InvoiceAddress object.

        Returns:
            InvoiceAddress: An empty InvoiceAddress object.
        """

        return InvoiceAddress(
            street=CitedValue(value="", spans=[], quote=None, reason=None),
            city=CitedValue(value="", spans=[], quote=None, reason=None),
            state=CitedValue(value="", spans=[], quote=None, reason=None),
            postal_code=CitedValue(value="", spans=[], quote=None, reason=None),
            country=CitedValue(value="", spans=[], quote=None, reason=None),
        )

    def to_dict(self):
        """
        Converts the InvoiceAddress object to a dictionary.

        Returns:
            dict: The InvoiceAddress object as a dictionary.
        """

        return {
            "street": self.street.value if self.street else None,
            "city": self.city.value if self.city else None,
            "state": self.state.value if self.state else None,
            "postal_code": self.postal_code.value if self.postal_code else None,
            "country": self.country.value if self.country else None,
            "phone": self.phone.value if self.phone else None,
        }


class InvoiceSignature(BaseModel):
    """
    A class representing a signature for an invoice.

    Attributes:
        signatory: Name of the person who signed the invoice.
        is_signed: Indicates if the invoice is signed.
    """

    signatory: Optional[CitedValue] = Field(
        None, description="Name of the person who signed the invoice"
    )
    is_signed: Optional[CitedValue] = Field(None, description="Indicates if the invoice is signed")

    @staticmethod
    def example():
        """
        Creates an empty example InvoiceSignature object.

        Returns:
            InvoiceSignature: An empty InvoiceSignature object
        """

        return InvoiceSignature(
            signatory=CitedValue(value="", spans=[], quote=None, reason=None),
            is_signed=CitedValue(value=False, spans=[], quote=None, reason=None),
        )

    def to_dict(self):
        """
        Converts the InvoiceSignature object to a dictionary.

        Returns:
            dict: The InvoiceSignature object as a dictionary.
        """

        return {
            "signatory": self.signatory.value if self.signatory else None,
            "is_signed": self.is_signed.value if self.is_signed else None,
        }


class InvoiceItem(BaseModel):
    """
    A class representing a line item in an invoice.

    Attributes:
        product_code: Product code, product number, or SKU associated with the line item.
        description: Description of the line item.
        quantity: Quantity of the line item.
        tax: Tax amount applied to the line item.
        tax_rate: Tax rate applied to the line item.
        unit_price: Net or gross price of one unit of the line item.
        total: The total charges associated with the line item.
        reason: Reason for returning the line item.
    """

    product_code: Optional[CitedValue] = Field(
        None, description="Product code, product number, or SKU associated with the line item, e.g. 12345",
    )
    description: Optional[CitedValue] = Field(
        None, description="Description of the line item, e.g. Product A",
    )
    quantity: Optional[CitedValue] = Field(
        None, description="Quantity of the line item",
    )
    tax: Optional[CitedValue] = Field(
        None, description="Tax amount applied to the line item, e.g. 6.00",
    )
    tax_rate: Optional[CitedValue] = Field(
        None, description="Tax rate applied to the line item, e.g. 18%",
    )
    unit_price: Optional[CitedValue] = Field(
        None, description="Net or gross price of one unit of the line item, e.g. 10.00",
    )
    total: Optional[CitedValue] = Field(
        None, description="The total charges associated with the line item, e.g. 100.00",
    )
    reason: Optional[CitedValue] = Field(
        None, description="Reason for returning the line item, e.g. Damaged",
    )

    @staticmethod
    def example():
        """
        Creates an empty example InvoiceItem object.

        Returns:
            InvoiceItem: An empty InvoiceItem object.
        """
        return InvoiceItem(
            product_code=CitedValue(value="", spans=[], quote=None, reason=None),
            description=CitedValue(value="", spans=[], quote=None, reason=None),
            quantity=CitedValue(value=0, spans=[], quote=None, reason=None),
            tax=CitedValue(value=0.0, spans=[], quote=None, reason=None),
            tax_rate=CitedValue(value="", spans=[], quote=None, reason=None),
            unit_price=CitedValue(value=0.0, spans=[], quote=None, reason=None),
            total=CitedValue(value=0.0, spans=[], quote=None, reason=None),
            reason=CitedValue(value="", spans=[], quote=None, reason=None),
        )

    def to_dict(self):
        """
        Converts the InvoiceItem object to a dictionary.

        Returns:
            dict: The InvoiceItem object as a dictionary.
        """

        return {
            "product_code": self.product_code.value if self.product_code else None,
            "description": self.description.value if self.description else None,
            "quantity": self.quantity.value if self.quantity else None,
            "tax": f"{self.tax.value:.2f}" if self.tax and self.tax.value is not None else None,
            "tax_rate": self.tax_rate.value if self.tax_rate else None,
            "unit_price": f"{self.unit_price.value:.2f}"
            if self.unit_price and self.unit_price.value is not None
            else None,
            "total": f"{self.total.value:.2f}" if self.total and self.total.value is not None else None,
            "reason": self.reason.value if self.reason else None,
        }


class Invoice(BaseModel):
    """
    A class representing an invoice.

    Attributes:
        customer_name: Name of the customer being invoiced.
        customer_address: Full address of the customer.
        customer_tax_id: Government tax ID of the customer.
        shipping_address: Full address of the shipping location for the customer.
        purchase_order: Purchase order reference number.
        invoice_id: Reference ID for the invoice.
        invoice_date: Date the invoice was issued.
        payable_by: Date when the invoice should be paid.
        vendor_name: Name of the vendor who created the invoice.
        vendor_address: Full address of the vendor.
        vendor_tax_id: Government tax ID of the vendor.
        remittance_address: Full address where the payment should be sent.
        subtotal: Subtotal of the invoice.
        total_discount: Total discount applied to the invoice.
        total_tax: Total tax applied to the invoice.
        invoice_total: Total charges associated with the invoice.
        payment_terms: Payment terms for the invoice.
        items: List of line items in the invoice.
        total_item_quantity: Total quantity of items in the invoice.
        items_customer_signature: Signature of the customer for the items in the invoice.
        items_vendor_signature: Signature of the vendor for the items in the invoice.
        returns: List of line items returned in the invoice.
        total_return_quantity: Total quantity of items returned in the invoice.
        returns_customer_signature: Signature of the customer for the returned items in the invoice.
        returns_vendor_signature: Signature of the vendor for the returned items in the invoice.
    """

    customer_name: Optional[CitedValue] = Field(
        None, description="Name of the customer being invoiced, e.g. Company A"
    )
    customer_address: Optional[InvoiceAddress] = Field(
        None, description="Full address of the customer, e.g. 123 Main St., City, Country"
    )
    customer_tax_id: Optional[CitedValue] = Field(
        None, description="Government tax ID of the customer, e.g. 123456789"
    )
    shipping_address: Optional[InvoiceAddress] = Field(
        None, description="Full address of the shipping location for the customer (null if the same as customer address), e.g. 123 Main St., City, Country"
    )
    purchase_order: Optional[CitedValue] = Field(
        None, description="Purchase order reference number, e.g. PO-1234"
    )
    invoice_id: Optional[CitedValue] = Field(
        None, description="Reference ID for the invoice (often invoice number), e.g. INV-1234"
    )
    invoice_date: Optional[CitedValue] = Field(
        None, description="Date the invoice was issued or delivered, e.g., 2021-01-01"
    )
    payable_by: Optional[CitedValue] = Field(
        None, description="Date when the invoice should be paid, e.g., 2021-01-15"
    )
    vendor_name: Optional[CitedValue] = Field(
        None, description="Name of the vendor who created the invoice, e.g. Company B"
    )
    vendor_address: Optional[InvoiceAddress] = Field(
        None, description="Full address of the vendor, e.g. 321 Main St., City, Country"
    )
    vendor_tax_id: Optional[CitedValue] = Field(
        None, description="Government tax ID of the vendor, e.g. 123456789"
    )
    remittance_address: Optional[InvoiceAddress] = Field(
        None, description="Full address where the payment should be sent (null if the same as vendor address), e.g. 321 Main St., City, Country"
    )
    subtotal: Optional[CitedValue] = Field(
        None, description="Subtotal of the invoice, e.g. 100.00"
    )
    total_discount: Optional[CitedValue] = Field(
        None, description="Total discount applied to the invoice, e.g. 10.00"
    )
    total_tax: Optional[CitedValue] = Field(
        None, description="Total tax applied to the invoice, e.g. 5.00"
    )
    invoice_total: Optional[CitedValue] = Field(
        None, description="Total charges associated with the invoice, e.g. 95.00"
    )
    payment_terms: Optional[CitedValue] = Field(
        None, description="Payment terms for the invoice, e.g. Net 90"
    )
    items: Optional[list[InvoiceItem]] = Field(
        description="List of line items in the invoice"
    )
    total_item_quantity: Optional[CitedValue] = Field(
        None, description="Total quantity of items in the invoice"
    )
    items_customer_signature: Optional[InvoiceSignature] = Field(
        description="Signature of the customer for the items in the invoice"
    )
    items_vendor_signature: Optional[InvoiceSignature] = Field(
        description="Signature of the vendor for the items in the invoice"
    )
    returns: Optional[list[InvoiceItem]] = Field(
        description="List of line items returned in the invoice"
    )
    total_return_quantity: Optional[CitedValue] = Field(
        None, description="Total quantity of items returned in the invoice"
    )
    returns_customer_signature: Optional[InvoiceSignature] = Field(
        description="Signature of the customer for the returned items in the invoice"
    )
    returns_vendor_signature: Optional[InvoiceSignature] = Field(
        description="Signature of the vendor for the returned items in the invoice"
    )

    @staticmethod
    def example():
        """
        Creates an empty example Invoice object.

        Returns:
            Invoice: An empty Invoice object.
        """

        return Invoice(
            customer_name=CitedValue(value="", spans=[], quote=None, reason=None),
            customer_address=InvoiceAddress.example(),
            customer_tax_id=CitedValue(value="", spans=[], quote=None, reason=None),
            shipping_address=InvoiceAddress.example(),
            purchase_order=CitedValue(value="", spans=[], quote=None, reason=None),
            invoice_id=CitedValue(value="", spans=[], quote=None, reason=None),
            invoice_date=CitedValue(value=datetime.now().strftime("%Y-%m-%d"), spans=[], quote=None, reason=None),
            payable_by=CitedValue(value=datetime.now().strftime("%Y-%m-%d"), spans=[], quote=None, reason=None),
            vendor_name=CitedValue(value="", spans=[], quote=None, reason=None),
            vendor_address=InvoiceAddress.example(),
            vendor_tax_id=CitedValue(value="", spans=[], quote=None, reason=None),
            remittance_address=InvoiceAddress.example(),
            subtotal=CitedValue(value=0.0, spans=[], quote=None, reason=None),
            total_discount=CitedValue(value=0.0, spans=[], quote=None, reason=None),
            total_tax=CitedValue(value=0.0, spans=[], quote=None, reason=None),
            invoice_total=CitedValue(value=0.0, spans=[], quote=None, reason=None),
            payment_terms=CitedValue(value="", spans=[], quote=None, reason=None),
            items=[InvoiceItem.example()],
            total_item_quantity=CitedValue(value=0.0, spans=[], quote=None, reason=None),
            items_customer_signature=InvoiceSignature.example(),
            items_vendor_signature=InvoiceSignature.example(),
            returns=[InvoiceItem.example()],
            total_return_quantity=CitedValue(value=0.0, spans=[], quote=None, reason=None),
            returns_customer_signature=InvoiceSignature.example(),
            returns_vendor_signature=InvoiceSignature.example(),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "Invoice":
        """Create an `Invoice` instance from a JSON string using Pydantic parsing."""
        return cls.model_validate_json(json_str)

    def to_dict(self) -> dict:
        """Convert the `Invoice` instance to a plain dictionary."""
        return self.model_dump()

    @classmethod
    def get_json_schema_definition(cls) -> dict[str, Any]:
        """Return JSON schema definition for use with OpenAI Responses API."""
        # Base schema generated by Pydantic
        schema = cls.model_json_schema()

        # Structured Outputs with strict mode require `additionalProperties: false`
        # on *all* object types, including those inside definitions/$defs.
        # Walk the schema tree and enforce this.
        def enforce_additional_properties_false(node: dict) -> None:
            if not isinstance(node, dict):
                return

            node_type = node.get("type")
            if node_type == "object":
                # Only set if not already present
                node.setdefault("additionalProperties", False)
                for prop_schema in node.get("properties", {}).values():
                    enforce_additional_properties_false(prop_schema)

            elif node_type == "array":
                items = node.get("items")
                if isinstance(items, dict):
                    enforce_additional_properties_false(items)

            # Recurse into definitions/$defs so nested models are also strict.
            # Pydantic v2 typically uses "$defs"; older versions may use "definitions".
            for defs_key in ("$defs", "definitions"):
                if defs_key in node and isinstance(node[defs_key], dict):
                    for def_schema in node[defs_key].values():
                        enforce_additional_properties_false(def_schema)

        enforce_additional_properties_false(schema)

        # Resolve all $ref references and remove $defs
        def resolve_all_refs(node: dict, defs: dict) -> dict:
            """Recursively resolve all $ref references and return resolved schema."""
            if not isinstance(node, dict):
                return node

            # If this is a $ref, resolve it
            if "$ref" in node:
                ref_path = node["$ref"]
                # Extract definition name from path like "#/$defs/CitedValue" or "#/definitions/CitedValue"
                if "/" in ref_path:
                    def_name = ref_path.split("/")[-1]
                    if def_name in defs:
                        # Recursively resolve the referenced definition
                        resolved = resolve_all_refs(defs[def_name].copy(), defs)
                        # Fix CitedValue.value type if this is CitedValue
                        if (
                            def_name == "CitedValue"
                            and isinstance(resolved, dict)
                            and "properties" in resolved
                            and "value" in resolved["properties"]
                        ):
                            value_prop = resolved["properties"]["value"]
                            # Make value nullable: use array type ["string", "null"] for nullable
                            # Remove anyOf/oneOf if present (strict mode doesn't support them well)
                            if "anyOf" in value_prop:
                                del value_prop["anyOf"]
                            if "oneOf" in value_prop:
                                del value_prop["oneOf"]
                            # Set nullable type as array: ["string", "null"]
                            value_prop["type"] = ["string", "null"]
                        return resolved
                # If we can't resolve it, return as-is (shouldn't happen)
                return node

            # Recursively resolve all nested objects
            result = {}
            for key, value in node.items():
                if key in ("$defs", "definitions"):
                    # Skip $defs - we're removing them
                    continue
                elif isinstance(value, dict):
                    result[key] = resolve_all_refs(value, defs)
                elif isinstance(value, list):
                    result[key] = [
                        resolve_all_refs(item, defs) if isinstance(item, dict) else item
                        for item in value
                    ]
                else:
                    result[key] = value

            return result

        # Get all definitions before resolving
        all_defs = {}
        for defs_key in ("$defs", "definitions"):
            if defs_key in schema:
                all_defs.update(schema[defs_key])

        # Resolve all references and remove $defs
        resolved_schema = resolve_all_refs(schema, all_defs)

        # Ensure $defs is completely removed
        if "$defs" in resolved_schema:
            del resolved_schema["$defs"]
        if "definitions" in resolved_schema:
            del resolved_schema["definitions"]

        # Fix all object types: OpenAI strict mode requires 'required' array for ALL object types
        def fix_anyof_required(node: dict) -> None:
            """Ensure ALL object types have 'required' array with all property keys.

            OpenAI strict mode requires that ALL objects (not just in anyOf/oneOf) have a
            'required' array that includes ALL property keys. This includes:
            - Root objects
            - Nested objects
            - Objects in anyOf/oneOf branches
            - Objects in array items
            
            Note: Even though fields are in 'required', they can still be optional/nullable
            if their type allows null (e.g., {"type": ["string", "null"]}). However, the field
            must be present in the JSON (even if null) - it cannot be omitted entirely.
            """
            if not isinstance(node, dict):
                return

            # Fix ALL object types first (including root and nested objects)
            if node.get("type") == "object" and "properties" in node:
                properties = node["properties"]
                # Ensure required array includes all property keys
                node["required"] = list(properties.keys())

            # Fix anyOf branches
            if "anyOf" in node and isinstance(node["anyOf"], list):
                for branch in node["anyOf"]:
                    if isinstance(branch, dict):
                        # Fix object types in anyOf
                        if branch.get("type") == "object":
                            if "properties" in branch:
                                properties = branch["properties"]
                                branch["required"] = list(properties.keys())
                        # Fix array items that are objects (e.g., items: list[InvoiceItem])
                        elif branch.get("type") == "array" and "items" in branch:
                            items_schema = branch["items"]
                            if isinstance(items_schema, dict) and items_schema.get("type") == "object":
                                if "properties" in items_schema:
                                    properties = items_schema["properties"]
                                    items_schema["required"] = list(properties.keys())
                        # Recursively fix nested structures
                        fix_anyof_required(branch)

            # Fix oneOf branches (same requirement)
            if "oneOf" in node and isinstance(node["oneOf"], list):
                for branch in node["oneOf"]:
                    if isinstance(branch, dict):
                        # Fix object types in oneOf
                        if branch.get("type") == "object":
                            if "properties" in branch:
                                properties = branch["properties"]
                                branch["required"] = list(properties.keys())
                        # Fix array items that are objects
                        elif branch.get("type") == "array" and "items" in branch:
                            items_schema = branch["items"]
                            if isinstance(items_schema, dict) and items_schema.get("type") == "object":
                                if "properties" in items_schema:
                                    properties = items_schema["properties"]
                                    items_schema["required"] = list(properties.keys())
                        fix_anyof_required(branch)

            # Also fix object types that appear in array items (even outside anyOf)
            if node.get("type") == "array" and "items" in node:
                items_schema = node["items"]
                if isinstance(items_schema, dict) and items_schema.get("type") == "object":
                    if "properties" in items_schema:
                        properties = items_schema["properties"]
                        items_schema["required"] = list(properties.keys())

            # Recursively process all nested objects, arrays, and properties
            # Process properties explicitly to ensure all nested objects get fixed
            if "properties" in node and isinstance(node["properties"], dict):
                for prop_schema in node["properties"].values():
                    if isinstance(prop_schema, dict):
                        fix_anyof_required(prop_schema)
            
            # Process all other nested structures
            for value in node.values():
                if isinstance(value, dict):
                    fix_anyof_required(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            fix_anyof_required(item)

        fix_anyof_required(resolved_schema)

        # Return the ResponseTextConfigParam.format object
        return {
            "type": "json_schema",
            "name": "invoice",
            "schema": resolved_schema,
            "strict": True,
        }
