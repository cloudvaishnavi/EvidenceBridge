"""
Regression tests for Model 4 Billing Reconciliation and Serial Number Extraction.

Verifies:
1. Exact KMC Hospital neurology consultation & imaging order:
   - Document title: NEUROLOGY CONSULTATION & IMAGING ORDER
   - Provider: KMC Hospital (Kasturba Medical College)
   - Procedure code: CPT 70551
   - Procedure: MRI Brain without contrast
   - Stated total billed charge: ₹5,500.00
   - Reconciliation status: PARTIAL_BILLING_UNAVAILABLE
   - Difference: None (no false discrepancy)
   - Line items: 0 (no fabricated line items)
   - Grounded benchmark comparison: within benchmark (ceiling ₹8,500)
2. CPT codes (e.g. CPT 70551, CPT 99213) are never treated as prices.
3. Serial numbers (1, 2) are never treated as monetary amounts.
4. Genuine itemized hospital bills still reconcile correctly (TOTAL_MATCH, TOTAL_MISMATCH).
5. Outpatient prescriptions remain Not Applicable for billing reconciliation (billing_reconciliation is None).
6. Documents with a stated total but no line items show partial billing information (PARTIAL_BILLING_UNAVAILABLE).
7. Documents without billing information remain appropriately Not Applicable.
"""

from datetime import datetime, timezone
import pytest
from app.models.schemas import BillingClassification, Claim, ExtractedFields, ProvenanceMetadata
from app.services.billing_reconciliation import billing_reconciliation_service
from app.services.ner import ner_service
from app.services.provenance import ProvenanceService


KMC_REPRODUCTION_TEXT = """NEUROLOGY CONSULTATION & IMAGING ORDER

KMC HOSPITAL (KASTURBA MEDICAL COLLEGE) - MANGALURU, KARNATAKA

Patient: 46-year-old female presenting with progressive unilateral headache, papilledema, and new focal neurological signs.

Procedure: CPT 70551 Magnetic Resonance Imaging (MRI) Brain without contrast.

Total Billed Charge: ₹5,500.00

Clinical Indication: Urgent neuroimaging indicated to evaluate focal intracranial pathology per clinical guidelines."""


# =========================================================================
# Test 1: The exact KMC Hospital imaging order reproduction case
# =========================================================================

def test_kmc_imaging_order_exact_reproduction():
    """Verify exact reproduction document extracts expected fields and produces partial billing reconciliation."""
    # 1. NER extraction
    entities = ner_service.extract_entities(KMC_REPRODUCTION_TEXT)
    grouped = ner_service.group_medical_information(KMC_REPRODUCTION_TEXT, entities)

    # Document title
    assert grouped.document_title is not None
    assert "NEUROLOGY CONSULTATION" in grouped.document_title.upper()

    # Provider
    assert grouped.hospital.hospital_name is not None
    assert "KMC HOSPITAL" in grouped.hospital.hospital_name.value.upper()

    # Procedure & Procedure Code
    assert grouped.clinical.procedure_code is not None
    assert grouped.clinical.procedure_code.value == "CPT 70551"

    assert grouped.clinical.procedure is not None
    assert "MRI Brain without contrast" in grouped.clinical.procedure.value

    # 2. Billing Extraction & Reconciliation
    assert billing_reconciliation_service.is_likely_bill(KMC_REPRODUCTION_TEXT) is True

    stated_total = billing_reconciliation_service.extract_stated_total(KMC_REPRODUCTION_TEXT)
    assert stated_total == 5500.0

    line_items = billing_reconciliation_service.parse_line_items(KMC_REPRODUCTION_TEXT)
    assert len(line_items) == 0, f"Expected 0 line items, got: {line_items}"

    rec = billing_reconciliation_service.reconcile_claim_billing(
        raw_ocr_text=KMC_REPRODUCTION_TEXT,
        extracted_total=stated_total,
    )

    assert rec.stated_total == 5500.0
    assert rec.itemized_sum == 0.0
    assert rec.difference is None, "Difference must be None for partial billing to avoid false mismatch"
    assert rec.classification == BillingClassification.PARTIAL_BILLING_UNAVAILABLE
    assert len(rec.line_items) == 0
    assert "Itemized Reconciliation Unavailable" in rec.summary_message
    assert any("individual charge verification cannot be performed" in exp for exp in rec.explanations)

    # Benchmark Grounding
    assert len(rec.benchmark_comparisons) >= 1
    bm = rec.benchmark_comparisons[0]
    assert bm.billed_amount == 5500.0
    assert bm.status == "WITHIN_BENCHMARK"
    assert "CPT 70551" in bm.service_or_item


# =========================================================================
# Test 2: CPT codes never treated as prices
# =========================================================================

def test_cpt_codes_never_treated_as_prices():
    """CPT codes such as CPT 70551, CPT 99213, CPT 71020 must never be parsed as prices."""
    text_with_cpts = """
    OUTPATIENT IMAGING REQUISITION
    KMC Hospital Mangaluru
    Procedure: CPT 70551 Magnetic Resonance Imaging Brain
    Follow-up: CPT 99213 Office or other outpatient visit
    Prior Study: CPT 71020 Radiologic examination chest
    Total Billed Charge: ₹6,200.00
    """
    line_items = billing_reconciliation_service.parse_line_items(text_with_cpts)
    extracted_amounts = [it.amount for it in line_items]

    # CPT codes must never be parsed as line item amounts
    assert 70551.0 not in extracted_amounts
    assert 99213.0 not in extracted_amounts
    assert 71020.0 not in extracted_amounts

    # Stated total must extract ₹6,200.00, not any CPT code
    stated = billing_reconciliation_service.extract_stated_total(text_with_cpts)
    assert stated == 6200.0


# =========================================================================
# Test 3: Serial numbers 1 and 2 never treated as monetary amounts
# =========================================================================

def test_serial_numbers_never_treated_as_monetary_amounts():
    """List numbers and serial numbers 1, 2 must never be parsed as monetary amounts."""
    text_with_serials = """
    CLINICAL MEDICATION ORDER
    1. Paracetamol 500mg - 1 tablet orally twice daily
    2. Amoxicillin 250mg - 1 capsule orally three times daily
    3. Pantoprazole 40mg - 1 tablet before breakfast
    """
    line_items = billing_reconciliation_service.parse_line_items(text_with_serials)
    assert len(line_items) == 0, f"Expected 0 line items from medicine list, got {line_items}"

    stated = billing_reconciliation_service.extract_stated_total(text_with_serials)
    assert stated is None, f"Expected no stated total from medicine list, got {stated}"


# =========================================================================
# Test 4: Genuine itemized hospital bill still reconciling correctly
# =========================================================================

def test_genuine_itemized_hospital_bill_reconciliation():
    """Genuine hospital bills with line items must reconcile correctly (TOTAL_MATCH & TOTAL_MISMATCH)."""
    # 4A: Exact Match
    matched_invoice = """
    Hospital: Davangere General Hospital
    1. Consultation: ₹500.00
    2. Ultrasound Scan: ₹1,500.00
    Total Billed: ₹2,000.00
    """
    rec_match = billing_reconciliation_service.reconcile_claim_billing(
        raw_ocr_text=matched_invoice,
        extracted_total=2000.0,
    )
    assert rec_match.classification == BillingClassification.TOTAL_MATCH
    assert rec_match.itemized_sum == 2000.0
    assert rec_match.stated_total == 2000.0
    assert rec_match.difference == 0.0
    assert len(rec_match.line_items) == 2

    # 4B: Mismatch
    mismatched_invoice = """
    Hospital: Davangere General Hospital
    1. Consultation: ₹500.00
    2. Ultrasound Scan: ₹1,500.00
    Total Billed: ₹3,000.00
    """
    rec_mismatch = billing_reconciliation_service.reconcile_claim_billing(
        raw_ocr_text=mismatched_invoice,
        extracted_total=3000.0,
    )
    assert rec_mismatch.classification == BillingClassification.TOTAL_MISMATCH
    assert rec_mismatch.itemized_sum == 2000.0
    assert rec_mismatch.stated_total == 3000.0
    assert rec_mismatch.difference == -1000.0


# =========================================================================
# Test 5: Prescription remaining Not Applicable for billing reconciliation
# =========================================================================

def test_prescription_remains_not_applicable_for_billing():
    """Prescriptions routed to verification must have billing reconciliation as Not Applicable (None)."""
    rx_text = """
    GREEN VALLEY FAMILY CLINIC
    Outpatient Prescription
    Patient Name: Aarav Sharma
    Date: 18 Nov 2026
    Sl. No.  Medicine                  Dosage    Frequency              Duration
    1        Cetirizine 10 mg Tablet   1 tablet  Once daily (at night)  5 days
    2        Fluticasone Nasal Spray   1 spray   Twice daily            7 days
    Advice: Drink fluids.
    """
    prov = ProvenanceService.create_provenance(
        original_text=rx_text,
        source_type="prescription",
        source_url=None,
        source_timestamp=datetime.now(timezone.utc),
    )
    claim = Claim(
        claim_id="CLM-RX-TEST",
        original_text=rx_text,
        source_type="prescription",
        timestamp=datetime.now(timezone.utc),
        extracted_fields=ExtractedFields(entity="Cetirizine"),
        confidence=0.95,
        provenance=prov,
    )
    # 1. Billing eligibility guard must reject prescriptions
    assert billing_reconciliation_service.is_likely_bill(rx_text) is False

    # 2. Line items & stated total must not extract monetary values from prescription
    line_items = billing_reconciliation_service.parse_line_items(rx_text)
    assert len(line_items) == 0, f"Expected 0 line items from prescription, got: {line_items}"

    stated = billing_reconciliation_service.extract_stated_total(rx_text)
    assert stated is None, f"Expected no stated total from prescription, got: {stated}"

    # 3. Direct billing reconciliation calls on text and claim must return None (Not Applicable)
    rec_from_claim = billing_reconciliation_service.reconcile_claim_billing(claim=claim)
    assert rec_from_claim is None, "Prescription Claim must not enter billing reconciliation"

    rec_from_text = billing_reconciliation_service.reconcile_claim_billing(text=rx_text)
    assert rec_from_text is None, "Prescription text must return None (Not Applicable) for billing reconciliation"

    # 4. Pipeline routing eligibility guard check
    source_t = getattr(claim, "source_type", "")
    is_billing_eligible = source_t == "hospital_bill" or (
        source_t != "prescription" and billing_reconciliation_service.is_likely_bill(claim.original_text)
    )
    assert is_billing_eligible is False, "Prescriptions must be ineligible for billing reconciliation"


# =========================================================================
# Test 6: Document with stated total but no line items showing partial billing information
# =========================================================================

def test_document_with_stated_total_no_line_items_partial_billing():
    """Consultation / imaging order with stated total shows PARTIAL_BILLING_UNAVAILABLE."""
    consultation_text = """
    APOLLO SPECIALTY CLINIC
    SPECIALIST CONSULTATION & ORDER
    Patient: Ramesh Kumar
    Consultation & Comprehensive Screening Package
    Total Billed Charge: ₹3,500.00
    """
    assert billing_reconciliation_service.is_likely_bill(consultation_text) is True
    stated = billing_reconciliation_service.extract_stated_total(consultation_text)
    assert stated == 3500.0

    rec = billing_reconciliation_service.reconcile_claim_billing(
        raw_ocr_text=consultation_text,
        extracted_total=stated,
    )

    assert rec.classification == BillingClassification.PARTIAL_BILLING_UNAVAILABLE
    assert rec.stated_total == 3500.0
    assert rec.difference is None
    assert len(rec.line_items) == 0
    assert "Itemized Reconciliation Unavailable" in rec.summary_message


# =========================================================================
# Test 7: Document without billing information remaining appropriately Not Applicable
# =========================================================================

def test_document_without_billing_info_not_applicable():
    """Clinical discharge summary or narrative without financial charges is not treated as a bill."""
    clinical_summary = """
    DEPARTMENT OF GENERAL MEDICINE
    CLINICAL DISCHARGE SUMMARY
    Patient: John Doe, 45-year-old male
    Chief Complaint: Intermittent high-grade fever with chills for 4 days.
    Diagnosis: Acute Viral Illness, resolving.
    Hospital Course: Patient admitted and treated with IV fluids, supportive care, and paracetamol.
    Condition at Discharge: Hemodynamically stable, afebrile for 48 hours.
    Follow-up: Review in OPD after 1 week if fever recurs.
    """
    # 1. Billing eligibility guard rejects documents without charges
    assert billing_reconciliation_service.is_likely_bill(clinical_summary) is False

    # 2. Line items & stated total must not extract monetary values
    line_items = billing_reconciliation_service.parse_line_items(clinical_summary)
    assert len(line_items) == 0, f"Expected 0 line items from discharge summary, got: {line_items}"

    stated = billing_reconciliation_service.extract_stated_total(clinical_summary)
    assert stated is None, f"Expected no stated total from discharge summary, got: {stated}"

    # 3. Direct billing reconciliation calls on text and claim must return None (Not Applicable)
    prov = ProvenanceService.create_provenance(
        original_text=clinical_summary,
        source_type="clinical_note",
        source_url=None,
        source_timestamp=datetime.now(timezone.utc),
    )
    claim = Claim(
        claim_id="CLM-CLINICAL-TEST",
        original_text=clinical_summary,
        source_type="clinical_note",
        timestamp=datetime.now(timezone.utc),
        extracted_fields=ExtractedFields(entity="Acute Viral Illness"),
        confidence=0.95,
        provenance=prov,
    )
    rec_from_claim = billing_reconciliation_service.reconcile_claim_billing(claim=claim)
    assert rec_from_claim is None, "Clinical summary Claim must not enter billing reconciliation"

    rec_from_text = billing_reconciliation_service.reconcile_claim_billing(text=clinical_summary)
    assert rec_from_text is None, "Clinical summary text must return None (Not Applicable) for billing reconciliation"

    # 4. Pipeline routing eligibility guard check
    source_t = getattr(claim, "source_type", "")
    is_billing_eligible = source_t == "hospital_bill" or (
        source_t != "prescription" and billing_reconciliation_service.is_likely_bill(claim.original_text)
    )
    assert is_billing_eligible is False, "Clinical notes without charges must be ineligible for billing reconciliation"


# =========================================================================
# Test 8: Combined prescription + pharmacy tax invoice reconciliation
# =========================================================================

def test_combined_prescription_pharmacy_invoice_reconciliation():
    """Verify combined prescription + pharmacy tax invoice undergoes full billing reconciliation."""
    pharmacy_invoice_text = """
    APOLLO PHARMACY & CLINICAL SERVICES
    TAX INVOICE / PRESCRIPTION DISPENSATION
    Invoice Number: PH-2026-00871
    Date: 20 Nov 2026
    Patient: Rajesh Patel
    Rx Medication Orders:

    Sl No | Description                  | Qty | Rate  | Amount
    1     | Paracetamol 500mg Tablets    | 10  | 3.00  | 30.00
    2     | Cetirizine 10mg Tablets      | 10  | 4.00  | 40.00
    3     | Amoxicillin 500mg Capsules   | 15  | 5.00  | 75.00

    Subtotal: ₹145.00
    GST (5%): ₹7.25
    Total Billed Amount: ₹152.25
    Amount Paid: ₹152.25
    Balance Due: ₹0.00
    """

    # 1. Billing eligibility guard: genuine invoice evidence takes precedence
    assert billing_reconciliation_service.is_likely_bill(pharmacy_invoice_text) is True

    # 2. Field extractions
    stated = billing_reconciliation_service.extract_stated_total(pharmacy_invoice_text)
    assert stated == 152.25

    subtotal = billing_reconciliation_service.extract_subtotal(pharmacy_invoice_text)
    assert subtotal == 145.00

    gst = billing_reconciliation_service.extract_tax_or_gst(pharmacy_invoice_text)
    assert gst == 7.25

    amount_paid = billing_reconciliation_service.extract_amount_paid(pharmacy_invoice_text)
    assert amount_paid == 152.25

    balance_due = billing_reconciliation_service.extract_balance_due(pharmacy_invoice_text)
    assert balance_due == 0.00

    # 3. Line items extraction
    line_items = billing_reconciliation_service.parse_line_items(pharmacy_invoice_text)
    assert len(line_items) == 3, f"Expected 3 itemized medicine entries, got: {line_items}"
    assert line_items[0].amount == 30.00
    assert line_items[1].amount == 40.00
    assert line_items[2].amount == 75.00
    assert "Paracetamol" in line_items[0].description
    assert "Cetirizine" in line_items[1].description
    assert "Amoxicillin" in line_items[2].description

    # 4. Reconciliation execution
    rec = billing_reconciliation_service.reconcile_claim_billing(
        text=pharmacy_invoice_text,
        extracted_total=stated,
    )
    assert rec is not None
    assert rec.itemized_sum == 145.00
    assert rec.stated_total == 152.25
    assert rec.tax_or_gst == 7.25
    assert rec.subtotal == 145.00
    assert rec.amount_paid == 152.25
    assert rec.balance_due == 0.00
    assert rec.difference == 0.00
    assert rec.classification == BillingClassification.TOTAL_MATCH
    assert "exactly match" in rec.summary_message.lower()

    # 5. Pipeline routing eligibility guard check
    prov = ProvenanceService.create_provenance(
        original_text=pharmacy_invoice_text,
        source_type="hospital_bill",
        source_url=None,
        source_timestamp=datetime.now(timezone.utc),
    )
    claim = Claim(
        claim_id="CLM-PHARMACY-TEST",
        original_text=pharmacy_invoice_text,
        source_type="hospital_bill",
        timestamp=datetime.now(timezone.utc),
        extracted_fields=ExtractedFields(entity="Paracetamol", cost_range="152.25"),
        confidence=0.95,
        provenance=prov,
    )
    rec_from_claim = billing_reconciliation_service.reconcile_claim_billing(claim=claim)
    assert rec_from_claim is not None
    assert rec_from_claim.classification == BillingClassification.TOTAL_MATCH
