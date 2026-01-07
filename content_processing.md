It explains why Azure Content Understanding (CU) + LLM + Images are used together, how the flow works, and how to implement it correctly.

# Invoice Extraction Pipeline  
**Azure Content Understanding + LLM (Text + Image)**

## Overview
This project extracts structured invoice data using a **two-stage approach**:

1. **Azure Content Understanding (CU)** for OCR and layout extraction  
2. **LLM** for semantic understanding and schema generation

Both **OCR text (markdown)** and **images** are passed to the LLM to achieve **high accuracy, auditability, and confidence scoring**.

---

## Why This Architecture Exists

### Problem
- OCR alone does not understand business meaning
- LLMs alone are expensive and unreliable at OCR
- Invoices contain layout-dependent meaning and OCR ambiguity

### Solution
Use each system **only for what it does best**:

| Component | Responsibility |
|---------|----------------|
| CU | Pixels → text, layout, geometry |
| LLM | Text → business schema |
| Image | Verification & correction |

---

## High-Level Flow



PDF / Image
↓
Azure Content Understanding
↓
OCR Text + Layout + Geometry (Markdown / JSON)
↓
LLM (Text-first, Image-verified)
↓
Structured Invoice Schema (JSON)
↓
Confidence Scoring (OCR + LLM)


---

## Step 1: Azure Content Understanding (CU)

### What CU Does
- OCR (words, lines)
- Table detection
- Page structure
- Bounding boxes
- OCR confidence

### What CU Does NOT Do
- ❌ Business understanding
- ❌ Invoice schema extraction
- ❌ Domain validation

CU is **deterministic document reading**, not reasoning.

---

## Step 2: Inputs Sent to the LLM

The LLM receives **three inputs**:

### 1️⃣ OCR / Layout Text (Markdown) — PRIMARY
This is the main signal for extraction.

Example:
```text
Invoice Number: INV-12310
Invoice Date: 2025-01-01

Items:
USB Cable   Qty 2   $10
Mouse       Qty 1   $20

Total: $40

2️⃣ Original Image — SECONDARY

The image is used only when:

OCR text is ambiguous (1 vs l)

Layout meaning is unclear

Symbols are missing ($, -)

Handwritten or stamped content exists

The LLM does not re-OCR everything.

3️⃣ Instructions + Output Schema

The LLM is instructed to:

Extract specific fields

Output strict JSON

Avoid explanations or extra text

How the LLM Extracts the Schema
Mental Model (Important)

Schema is extracted from text.
Images are used only to verify or fix errors.

Actual Behavior

Read OCR markdown

Follow layout and tables

Map labels to schema fields

Validate consistency

Use image only if text is uncertain

Emit structured JSON

The LLM does not parse pixels directly into schema.

Example: OCR Error Correction

OCR output:

Invoice Number: INV-123l0


Image shows:

INV-12310


LLM behavior:

Detects suspicious OCR

Checks image

Corrects the value

Without the image, the wrong value would be returned confidently.

Confidence Scoring Strategy
Two Independent Signals
1️⃣ OCR Confidence (from CU)

How reliable was the text extraction?

2️⃣ LLM Token Logprobs

How confident was the model when generating the value?

Best Practice

Combine both signals

Flag low-confidence fields for manual review

Why Not Markdown Only?

Markdown-only extraction fails when:

OCR is wrong

Layout meaning is lost

Handwritten or stamped data exists

Audit evidence is required

Markdown gives speed, not guaranteed correctness.

Why Not Image Only?

Image-only extraction:

Is slower

Is more expensive

Loses deterministic layout

Makes confidence unreliable

CU already solves OCR better and cheaper.

Recommended Production Pattern
Adaptive Input Strategy

Always pass OCR markdown

Pass images when:

OCR confidence < threshold

Field is critical (invoice number, total)

Document is scanned or handwritten

This balances accuracy, cost, and latency.

Key Takeaways

CU reads the document

LLM understands the document

Images verify the document

Schema comes from text, not pixels

Confidence comes from OCR + LLM

One-Line Summary

Azure Content Understanding reads.
The LLM reasons.
Images keep both honest.