from __future__ import annotations
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


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

    street: Optional[str] = Field(description="Street address, e.g. 123 Main St.")
    city: Optional[str] = Field(description="City, e.g. New York")
    state: Optional[str] = Field(description="State, e.g. NY")
    postal_code: Optional[str] = Field(description="Postal code, e.g. 10001")
    country: Optional[str] = Field(description="Country, e.g. USA.")
    phone: Optional[str] = Field(description="Phone number, e.g. +1-123-456-7890.")

    @staticmethod
    def example():
        """
        Creates an empty example InvoiceAddress object.

        Returns:
            InvoiceAddress: An empty InvoiceAddress object.
        """

        return InvoiceAddress(street="", city="", state="", postal_code="", country="")

    def to_dict(self):
        """
        Converts the InvoiceAddress object to a dictionary.

        Returns:
            dict: The InvoiceAddress object as a dictionary.
        """

        return {
            "street": self.street,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country,
            "phone": self.phone,
        }


class InvoiceSignature(BaseModel):
    """
    A class representing a signature for an invoice.

    Attributes:
        signatory: Name of the person who signed the invoice.
        is_signed: Indicates if the invoice is signed.
    """

    signatory: Optional[str] = Field(
        description="Name of the person who signed the invoice"
    )
    is_signed: Optional[bool] = Field(description="Indicates if the invoice is signed")

    @staticmethod
    def example():
        """
        Creates an empty example InvoiceSignature object.

        Returns:
            InvoiceSignature: An empty InvoiceSignature object
        """

        return InvoiceSignature(signatory="", is_signed=False)

    def to_dict(self):
        """
        Converts the InvoiceSignature object to a dictionary.

        Returns:
            dict: The InvoiceSignature object as a dictionary.
        """

        return {"signatory": self.signatory, "is_signed": self.is_signed}


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

    product_code: Optional[str] = Field(
        description="Product code, product number, or SKU associated with the line item, e.g. 12345",
    )
    description: Optional[str] = Field(
        description="Description of the line item, e.g. Product A",
    )
    quantity: Optional[int] = Field(
        description="Quantity of the line item",
    )
    tax: Optional[float] = Field(
        description="Tax amount applied to the line item, e.g. 6.00",
    )
    tax_rate: Optional[str] = Field(
        description="Tax rate applied to the line item, e.g. 18%",
    )
    unit_price: Optional[float] = Field(
        description="Net or gross price of one unit of the line item, e.g. 10.00",
    )
    total: Optional[float] = Field(
        description="The total charges associated with the line item, e.g. 100.00",
    )
    reason: Optional[str] = Field(
        description="Reason for returning the line item, e.g. Damaged",
    )

    @staticmethod
    def example():
        """
        Creates an empty example InvoiceItem object.

        Returns:
            InvoiceItem: An empty InvoiceItem object.
        """
        return InvoiceItem(
            product_code="",
            description="",
            quantity=0.0,
            tax=0.0,
            tax_rate="",
            unit_price=0.0,
            total=0.0,
            reason="",
        )

    def to_dict(self):
        """
        Converts the InvoiceItem object to a dictionary.

        Returns:
            dict: The InvoiceItem object as a dictionary.
        """

        return {
            "product_code": self.product_code,
            "description": self.description,
            "quantity": self.quantity,
            "tax": f"{self.tax:.2f}" if self.tax is not None else None,
            "tax_rate": self.tax_rate,
            "unit_price": f"{self.unit_price:.2f}"
            if self.unit_price is not None
            else None,
            "total": f"{self.total:.2f}" if self.total is not None else None,
            "reason": self.reason,
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

    customer_name: Optional[str] = Field(
        description="Name of the customer being invoiced, e.g. Company A"
    )
    customer_address: Optional[InvoiceAddress] = Field(
        description="Full address of the customer, e.g. 123 Main St., City, Country"
    )
    customer_tax_id: Optional[str] = Field(
        description="Government tax ID of the customer, e.g. 123456789"
    )
    shipping_address: Optional[InvoiceAddress] = Field(
        description="Full address of the shipping location for the customer (null if the same as customer address), e.g. 123 Main St., City, Country"
    )
    purchase_order: Optional[str] = Field(
        description="Purchase order reference number, e.g. PO-1234"
    )
    invoice_id: Optional[str] = Field(
        description="Reference ID for the invoice (often invoice number), e.g. INV-1234"
    )
    invoice_date: Optional[str] = Field(
        description="Date the invoice was issued or delivered, e.g., 2021-01-01"
    )
    payable_by: Optional[str] = Field(
        description="Date when the invoice should be paid, e.g., 2021-01-15"
    )
    vendor_name: Optional[str] = Field(
        description="Name of the vendor who created the invoice, e.g. Company B"
    )
    vendor_address: Optional[InvoiceAddress] = Field(
        description="Full address of the vendor, e.g. 321 Main St., City, Country"
    )
    vendor_tax_id: Optional[str] = Field(
        description="Government tax ID of the vendor, e.g. 123456789"
    )
    remittance_address: Optional[InvoiceAddress] = Field(
        description="Full address where the payment should be sent (null if the same as vendor address), e.g. 321 Main St., City, Country"
    )
    subtotal: Optional[float] = Field(
        description="Subtotal of the invoice, e.g. 100.00"
    )
    total_discount: Optional[float] = Field(
        description="Total discount applied to the invoice, e.g. 10.00"
    )
    total_tax: Optional[float] = Field(
        description="Total tax applied to the invoice, e.g. 5.00"
    )
    invoice_total: Optional[float] = Field(
        description="Total charges associated with the invoice, e.g. 95.00"
    )
    payment_terms: Optional[str] = Field(
        description="Payment terms for the invoice, e.g. Net 90"
    )
    items: Optional[list[InvoiceItem]] = Field(
        description="List of line items in the invoice"
    )
    total_item_quantity: Optional[float] = Field(
        description="Total quantity of items in the invoice"
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
    total_return_quantity: Optional[float] = Field(
        description="Total quantity of items returned in the invoice"
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
            customer_name="",
            customer_address=InvoiceAddress.example(),
            customer_tax_id="",
            shipping_address=InvoiceAddress.example(),
            purchase_order="",
            invoice_id="",
            invoice_date=datetime.now().strftime("%Y-%m-%d"),
            payable_by=datetime.now().strftime("%Y-%m-%d"),
            vendor_name="",
            vendor_address=InvoiceAddress.example(),
            vendor_tax_id="",
            remittance_address=InvoiceAddress.example(),
            subtotal=0.0,
            total_discount=0.0,
            total_tax=0.0,
            invoice_total=0.0,
            payment_terms="",
            items=[InvoiceItem.example()],
            total_item_quantity=0.0,
            items_customer_signature=InvoiceSignature.example(),
            items_vendor_signature=InvoiceSignature.example(),
            returns=[InvoiceItem.example()],
            total_return_quantity=0.0,
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

        # Return the ResponseTextConfigParam.format object
        return {
            "type": "json_schema",
            "name": "invoice",
            "schema": schema,
            "strict": True,
        }
