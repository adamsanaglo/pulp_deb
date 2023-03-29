from pathlib import Path

import pytest

from pmc.auth import pmcauth

assets = Path.cwd() / "tests" / "assets"


@pytest.mark.parametrize("pem_file", [f for f in assets.glob("*.pem")])
def test_find_leaf_cert(pem_file: Path) -> None:
    cert = pem_file.read_text()

    cert_chain = pmcauth._parse_certs_from_text(cert)
    cert_chain_length = len(cert_chain)
    assert cert_chain_length > 0

    if cert_chain_length > 1:
        leaf_cert = pmcauth._remove_cas_from_chain(cert_chain)
        assert len(leaf_cert) == 1
