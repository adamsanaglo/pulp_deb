
import json
import time
from typing import Tuple
from urllib.parse import ParseResult, urlunparse

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError
from requests.packages.urllib3.util.retry import Retry


# noinspection PyPep8Naming
class keyvault_util:
    """
    A simple class for handling basic KeyVault functionality
    """

    def __init__(self, suffix: str = 'vault.azure.net', client_id: str = '', token: str = ''):
        """
        Create a KeyVaultClient using credentials
        received from MSI.
        """
        self.suffix = suffix
        self.max_retries = 6
        self._set_https_session()
        self.client_id = client_id
        if token:
            # User supplied token
            self.token = token
            return

        success, msg = self._try_get_identity_token()
        if success:
            return
        raise Exception(f'Failed to get Identity token: [{msg}]')

    def _try_get_identity_token(self) -> Tuple[bool, str]:
        """
        Attempts to get AAD token for KeyVault using IMDS
        - If successful, return True and empty string
        - If failed, return False and an error message
        """
        headers = {'Metadata': 'true'}
        resource = f'https://{self.suffix}'
        params = f'api-version=2021-02-01&resource={resource}'
        imds_url = f'http://169.254.169.254/metadata/identity/oauth2/token?{params}'
        if self.client_id:
            # VM has multiple identities - specify which ID to use
            imds_url = f"{imds_url}&client_id={self.client_id}"
        error_prefix = 'Failed to get token from IMDS due to'
        try:
            resp = self.session.get(imds_url, headers=headers)
        except ConnectionError as ex:
            return False, f'{error_prefix} connection error: {ex}'
        if resp.status_code != 200:
            return False, f'{error_prefix} status code {resp.status_code}'
        try:
            self.token = json.loads(resp.text)['access_token']
        except ValueError as ex:
            return False, f'{error_prefix} JSON decoding error: {ex}'
        except KeyError:
            return False, f'{error_prefix} missing JSON key [access_token]'
        return True, ''

    def _set_https_session(self):
        '''
        Creates a session object which will be used for requests
        with pre-defined retry rules
        '''
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session = requests.Session()
        self.session.mount("https://", adapter)

    def _get_url(self, vault_url: str) -> dict:
        """
        Gets the specified URL from KeyVault using the auth token
        """
        return self._query_url(vault_url, "get")

    def _post_url(self, vault_url: str, data: dict) -> dict:
        """
        Posts to the specifiec KeyVault URL using the auth token
        """
        return self._query_url(vault_url, "post", data)

    def _query_url(self, vault_url: str, operation: str = "get", data: dict = None) -> dict:
        """
        Perform arbitrary HTTP operation against KeyVault using the auth token
        """
        msg_template = "Connection Error reaching"
        allowed_responses = {
            "get": [200],
            "post": [202]
        }
        if operation not in allowed_responses:
            # Request is neither get nor post
            raise Exception(f"Operation {operation} is not valid [{','.join(allowed_responses)}]")
        try:
            if operation == "post":
                resp = self.session.post(vault_url, headers={'Authorization': f'Bearer {self.token}'}, json = data)
            else:
                resp = self.session.get(vault_url, headers={'Authorization': f'Bearer {self.token}'})
        except ConnectionError as ex:
            raise ConnectionError(f'{msg_template} {vault_url}: {ex}')
        if resp.status_code not in allowed_responses[operation]:
            detail = f'Status code: {resp.status_code}'
            raise Exception(f'{msg_template} {vault_url}: {detail}')
        return json.loads(resp.text)

    def _get_secret_path(self, vault: str, secret: str, version: str, secret_type: str = 'secrets', api_version: str = "7.3") -> str:
        """
        Return the full URL for the specified secret/certificate
        """
        secret_version = '/' + version if version else ''
        path = f'{secret_type}/{secret}{secret_version}'
        parsed = ParseResult(scheme='https',
                             netloc=f'{vault}.{self.suffix}',
                             path=path,
                             query=f'api-version={api_version}',
                             params='',
                             fragment='')
        return urlunparse(parsed)

    def _get_secret(self, vault: str, secret: str, version: str = '') -> dict:
        """
        Get the object representing the latest secret,
        so that the value itself and other metadata can be extracted
        """
        vault_url = self._get_secret_path(vault, secret, version)
        return self._get_url(vault_url)

    def get_secret(self, vault: str, secret: str, version: str = '') -> str:
        """
        Get the specified version of the specified secret
        from the specified KeyVault.
        """
        return self._get_secret(vault, secret, version)['value']
    
    def get_cert_policy(self, vault: str, cert_name: str):
        """
        Fetch the certificate issuance policy, which is required
        to rotate the cert.
        """
        url = self._get_secret_path(vault, cert_name, 'policy', 'certificates')
        res = self._get_url(url)
        return res

    def rotate_cert(self, vault: str, cert_name: str):
        """
        Generate a new cert using the existing issuance policy
        """
        # Retrieve the issuance policy for this cert
        cert_policy = self.get_cert_policy(vault, cert_name)
        url = self._get_secret_path(vault, cert_name, 'create', 'certificates')
        data = {
            "policy": cert_policy
        }
        # Request a new cert
        res = self._post_url(url, data)
        url = self._get_secret_path(vault, cert_name, 'pending', 'certificates')
        status = res["status"]
        # Poll for completion
        while status == "inProgress":
            time.sleep(5)
            res = self._get_url(url)
            status = res["status"]
        if status == "completed":
            # Success
            return
        raise Exception(f"Unable to rotate cert {vault}/{cert_name}: {res[status_details]}")