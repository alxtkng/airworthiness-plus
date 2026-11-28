"""Provider contract and local signing test double for synthetic evidence only."""

from dataclasses import asdict, dataclass
from typing import Literal, Protocol

from django.core.signing import Signer

Status = Literal["pending", "declined", "signed"]


@dataclass(frozen=True)
class Request:
    reference: str
    signer: str
    sha256: str
    document: bytes


@dataclass(frozen=True)
class Result:
    status: Status
    reference: str = ""
    signer: str = ""
    sha256: str = ""
    proof: str = ""

    def evidence(self) -> dict[str, str]:
        return asdict(self)


class Provider(Protocol):
    name: str

    def check(self, request: Request) -> Result:
        """Request or poll using the same idempotency reference."""

    def verifies(self, result: Result) -> bool:
        """Validate provider proof under this provider's documented trust policy."""


class SyntheticProvider:
    name = "local-training-test-double-v1"

    @staticmethod
    def _signer() -> Signer:
        return Signer(salt="planning.signing-provider.training-v1")

    def check(self, request: Request) -> Result:
        proof = self._signer().signature(
            _binding(request.reference, request.signer, request.sha256)
        )
        return Result("signed", request.reference, request.signer, request.sha256, proof)

    def verifies(self, result: Result) -> bool:
        from django.utils.crypto import constant_time_compare

        expected = self._signer().signature(
            _binding(result.reference, result.signer, result.sha256)
        )
        return constant_time_compare(expected, result.proof)


def _binding(reference: str, signer: str, sha256: str) -> str:
    return f"{reference}:{signer}:{sha256}"


def provider() -> Provider:
    return SyntheticProvider()
