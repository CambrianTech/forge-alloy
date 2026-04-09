"""photo-provenance — Camera enclave → edits → publish chain of custody.

Stub domain that proves the registry mechanism is genuinely non-ML. The
photo-provenance use case from forge-alloy's APPLICATIONS.md:

    A camera enclave signs the original capture (capture stage), every
    edit in Photoshop / Lightroom / Affinity Photo records a signed
    edit stage with the operation type and the editor's enclave key,
    and the publish step on social media records the final stage with
    the QR code embedded in EXIF. Anyone with the alloy can walk the
    full chain of custody from sensor to feed and verify cryptographically
    that no edit happened off-chain.

The actual stage schemas are placeholders today — when the first real
photo-provenance use case ships, this file gets the real Pydantic models
for capture / edit / publish stages and a real CameraAttestation +
EditAttestation root extension. For now the stub is a witness that the
registry handles non-ML domains without any change to the universal core
or to llm_forge.

Reproducibility contract: photo-provenance alloys are NOT in the test
catalog yet (no published artifacts use this domain). When they ship,
add them to the regression test alongside the continuum-ai/* alloys.
"""

from __future__ import annotations

from .base import DomainExtension


class PhotoProvenanceDomain(DomainExtension):
    """photo-provenance domain extension. Registered against id 'photo-provenance'."""

    id = "photo-provenance"

    def stage_types(self) -> dict[str, type]:
        """Stage types this domain owns. Currently empty stubs.

        Real schemas would be:
            capture       → CameraCaptureStage
                            (sensorId, gpsHash, exif, signature)
            edit          → PhotoEditStage
                            (tool, operation, parameters, signature)
            publish       → PhotoPublishStage
                            (platform, postId, qrEmbed, signature)

        The stage type strings are placeholders pending the first real
        photo-provenance artifact's schema.
        """
        return {
            # Placeholder — concrete schemas land when the first
            # photo-provenance artifact ships.
        }

    def root_extensions(self) -> dict[str, type]:
        """Root-extension fields. Currently empty.

        Future:
            cameraAttestation  → CameraAttestation
                                 (enclave certificate, public key,
                                  attestation timestamp)
        """
        return {}
