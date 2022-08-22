from typing import List

from msal import ConfidentialClientApplication
from OpenSSL.crypto import FILETYPE_PEM, X509, dump_certificate, load_certificate

from .schemas import Config


class pmcauth:
    def __init__(self, config: Config):
        """
        Initialize an instance of pmcauth
        """
        self.scope = config.msal_scope
        self.client_certificate_contents = config.msal_cert_path.expanduser().read_text()
        # Find the leaf cert and thumbprint
        self.leaf_cert = self.find_leaf_cert()
        self.client_certificate_thumbprint = self._get_cert_thumbprint()
        client_credential = {
            "thumbprint": self.client_certificate_thumbprint,
            "private_key": self.client_certificate_contents,
        }

        if config.msal_SNIAuth:
            # Include the leaf cert, for SNIssuer Auth
            client_credential["public_certificate"] = self.leaf_cert  # Todo - parse cert
        self.app = ConfidentialClientApplication(
            config.msal_client_id,
            authority=config.msal_authority,
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

        raise Exception(result.get("error"))

    def _get_cert_thumbprint(self) -> str:
        """
        Return the thumbprint for the leaf certificate associated with this client
        """
        cert = load_certificate(FILETYPE_PEM, self.leaf_cert.encode("utf-8"))
        return cert.digest("sha1").decode("utf-8").replace(":", "")

    def find_leaf_cert(self) -> str:
        """
        From the certificate contents that were read by the client,
        find the leaf cert.
        :returns str: leaf cert in str/PEM form
        """
        certs = self._parse_certs_from_text()
        if len(certs) == 0:
            # No certs present - must only be private key
            raise Exception("Found no leaf certificates in specified cert!")
        if len(certs) > 1:
            # Cert chain is present - remove root/intermediary CA's.
            certs = pmcauth._remove_cas_from_chain(certs)
        # Only one cert present - must be the leaf cert
        return dump_certificate(FILETYPE_PEM, certs[0]).decode("utf-8")

    def _parse_certs_from_text(self) -> List[X509]:
        """
        Given one or more certificates in string/PEM form,
        parse them to a list of X509 objects
        :returns: list of one or more X509 certificate objects
        """
        lines = self.client_certificate_contents.split("\n")
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
        issuer = ca_cert.get_issuer().CN
        while len(certs) > 1:
            # Loop through certs, removing intermediaries until we find the leaf cert
            intermediary = next(cert for cert in certs if cert.get_issuer().CN == issuer)
            certs.remove(intermediary)
            issuer = intermediary.get_issuer().CN
        return certs