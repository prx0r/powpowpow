"""
UKGraph Core — Receipt (QP-lite).

From SPEC.md section 29:
"Sensitive raw values should remain private where possible.
Use commitments/hashes/references when the ledger does not need plaintext."
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
from enum import Enum


class Actuality(Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


@dataclass
class Receipt:
    """Evidence that a real-world outcome occurred.
    
    From SPEC.md:
    "What external evidence is sufficient to claim this real-world outcome occurred?"
    """
    receipt_id: str
    
    goal: str = ""
    route_id: str = ""
    
    # When
    attempted_at: str = ""      # ISO UTC
    
    # What proof
    proof_rule: str = ""        # e.g. "SUBMISSION_ACKNOWLEDGED"
    proof_rule_version: str = ""
    
    # Evidence
    evidence: list = field(default_factory=list)  # list of Evidence objects
    
    # Outcome
    result: str = "UNKNOWN"    # TRUE, FALSE, UNKNOWN
    
    # When settled
    settled_at: str = ""
    
    # Private data (hashed, not stored in plaintext)
    private_commitment: str = ""  # hash of sensitive data
    
    def settle(self, actuality: str):
        """Settle the receipt with an outcome."""
        self.result = actuality
        self.settled_at = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> dict:
        return {
            "receipt_id": self.receipt_id,
            "goal": self.goal,
            "route_id": self.route_id,
            "attempted_at": self.attempted_at,
            "proof_rule": self.proof_rule,
            "proof_rule_version": self.proof_rule_version,
            "evidence": self.evidence,
            "result": self.result,
            "settled_at": self.settled_at,
        }


# Reusable proof rules (from SPEC.md section 28)

PROOF_RULES = {
    "SUBMISSION_ACKNOWLEDGED": "Submission was acknowledged by the target system",
    "BOOKING_CONFIRMED": "Booking was confirmed with a reference number",
    "PAYMENT_SETTLED": "Payment was processed",
    "PAYMENT_RECEIVED": "Payment was received by the recipient",
    "APPLICATION_ACCEPTED": "Application was accepted (not just submitted)",
    "ACCOUNT_STATE_CHANGED": "Account state changed as expected",
    "PERMIT_ISSUED": "Permit or licence was issued",
    "DOCUMENT_ISSUED": "Document was issued",
    "ITEM_SOLD": "Item was sold at the expected price",
    "SERVICE_COMPLETED": "Service was completed satisfactorily",
    "CONTRACT_AWARDED": "Contract was awarded to the applicant",
    "REFUND_RECEIVED": "Refund was received",
}
