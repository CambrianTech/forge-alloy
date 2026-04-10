"""ticketing — Venue ticket batches with cryptographic chain of custody.

Stub domain that proves the registry mechanism handles non-ML use cases
beyond photo-provenance too. The ticketing use case from forge-alloy's
APPLICATIONS.md:

    A venue's box office issues a batch of tickets (issued stage), each
    transfer between users records a signed transferred stage, and the
    gate scanner records the final stage at admission (scanned). The
    alloy carries the full chain of custody from issuer to gate, so a
    counterfeit ticket can be detected by walking the chain and
    verifying every signature is from a key that was authorized at
    that step.

Same shape as photo-provenance: stub today, real Pydantic models when
the first real ticketing artifact ships.

Reproducibility contract: ticketing alloys are NOT in the test catalog
yet. When the first venue / FedEx / concert use case lands, the schemas
get filled in and the regression test grows to cover them.
"""

from __future__ import annotations

from .base import DomainExtension


class TicketingDomain(DomainExtension):
    """ticketing domain extension. Registered against id 'ticketing'."""

    id = "ticketing"

    def stage_types(self) -> dict[str, type]:
        """Stage types this domain owns. Currently empty stubs.

        Real schemas would be:
            issued         → TicketIssuedStage
                             (venue, eventId, seat, holder,
                              issuerSignature, issuedAt)
            transferred    → TicketTransferredStage
                             (fromHolder, toHolder, fromSignature,
                              toSignature, transferredAt)
            scanned        → TicketScannedStage
                             (gate, scannerId, scannerSignature,
                              admit | deny, scannedAt)
        """
        return {}

    def root_extensions(self) -> dict[str, type]:
        return {}
