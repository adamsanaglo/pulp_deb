from pathlib import Path
from typing import List, Optional

from msal import ConfidentialClientApplication
from OpenSSL.crypto import FILETYPE_PEM, X509, dump_certificate, load_certificate


class AuthenticationError(Exception):
    def __init__(self, message: str, detail: str = "") -> None:
        super().__init__(message)
        self.detail = detail


class pmcauth:
    def __init__(
        self,
        msal_client_id: str,
        msal_scope: str,
        msal_authority: str,
        msal_cert_path: Optional[Path] = None,
        msal_cert: Optional[str] = None,
        msal_SNIAuth: bool = True,
    ):
        """
        Initialize an instance of pmcauth
        """
        if msal_cert:
            self.client_certificate_contents = msal_cert
        elif msal_cert_path:
            self.client_certificate_contents = msal_cert_path.expanduser().read_text()
        else:
            raise AuthenticationError("No MSAL cert path or cert set for authentication.")

        self.scope = msal_scope
        # Find the leaf cert and thumbprint
        self.leaf_cert = self.find_leaf_cert()
        self.client_certificate_thumbprint = self._get_cert_thumbprint()
        client_credential = {
            "thumbprint": self.client_certificate_thumbprint,
            "private_key": self.client_certificate_contents,
        }

        if msal_SNIAuth:
            # Include the leaf cert, for SNIssuer Auth
            client_credential["public_certificate"] = self.leaf_cert  # Todo - parse cert
        self.app = ConfidentialClientApplication(
            msal_client_id,
            authority=msal_authority,
            client_credential=client_credential,
        )

    def acquire_token(self) -> str:
        """
        Retrieve a token from cache or AAD.
        Raise Exception if unable to retrieve token.
        """
        result = self.app.acquire_token_silent([self.scope], account=None)
        if not result:
            # No token in cache; retrieve from AAD
            result = self.app.acquire_token_for_client(scopes=[self.scope])

        if "access_token" in result:
            return str(result["access_token"])

        raise AuthenticationError(
            result.get("error") or "failed to acquire token",
            detail=result.get("error_description"),
        )

    def _get_cert_thumbprint(self) -> str:
        """
        Return the thumbprint for the leaf certificate associated with this client
        """
        cert = load_certificate(FILETYPE_PEM, self.leaf_cert.encode("utf-8"))
        return cert.digest("sha1").decode("utf-8").replace(":", "")

    def find_leaf_cert(self) -> str:
        """
        From the certificate contents that were obtained by the client,
        find the leaf cert.
        :returns str: leaf cert in str/PEM form
        """
        certs = self._parse_certs_from_text(self.client_certificate_contents)
        if len(certs) == 0:
            # No certs present - could be a private key or invalid cert
            raise AuthenticationError(
                "Failed to parse MSAL certificate. Found no leaf certificates in specified cert. "
                "Is your cert a valid pem?"
            )
        if len(certs) > 1:
            # Cert chain is present - remove root/intermediary CA's.
            certs = pmcauth._remove_cas_from_chain(certs)
        # Only one cert present - must be the leaf cert
        return dump_certificate(FILETYPE_PEM, certs[0]).decode("utf-8")

    @staticmethod
    def _parse_certs_from_text(client_certificate_contents: str) -> List[X509]:
        """
        Given one or more certificates in string/PEM form,
        parse them to a list of X509 objects
        :returns: list of one or more X509 certificate objects
        """
        lines = client_certificate_contents.splitlines()
        certs = []
        cert_tmp = []
        for line in lines:
            if line == "-----BEGIN CERTIFICATE-----":
                # Start capturing a new certificate
                cert_tmp = [line]
            elif line == "-----END CERTIFICATE-----":
                # Finish capturing a certificate
                cert_tmp.append(line)
                certs.append(
                    load_certificate(FILETYPE_PEM, "\n".join(cert_tmp).encode(encoding="utf-8"))
                )
                cert_tmp = []
            elif cert_tmp:
                # Continue existing entry
                cert_tmp.append(line)
        return certs

    @staticmethod
    def _remove_cas_from_chain(certs: List[X509]) -> List[X509]:
        """
        Given a list of X509 objects, remove all CA's/intermediaries
        leaving only the leaf cert.
        This is done by finding the first self-signed cert then removing
        each cert in the chain until only one is left.

        :param list certs: list containing one or more certs
        :returns: list containing only the leaf cert
        """
        # Identify and remove the CA
        ca_cert = next(cert for cert in certs if cert.get_issuer().CN == cert.get_subject().CN)
        certs.remove(ca_cert)
        # Root CA's subject is the issuer of the next cert in the chain
        issuer = ca_cert.get_subject().CN
        while len(certs) > 1:
            # Loop through certs, removing intermediaries until we find the leaf cert
            try:
                intermediary = next(cert for cert in certs if cert.get_issuer().CN == issuer)
            except StopIteration:
                raise AuthenticationError("Unable to find leaf certificate in cert chain")
            certs.remove(intermediary)
            # This intermediary (known by its subject) issued the next cert in the chain
            issuer = intermediary.get_subject().CN
        return certs
