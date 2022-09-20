# Copy of https://microsoft.visualstudio.com/OSGCXE/_git/csd.apt.linux?path=/repoapi_client/azure/repoclient/repolib.py

import json
import os
import re
import requests
import sys
import time
import uuid

from OpenSSL.crypto import dump_certificate, load_certificate, FILETYPE_PEM, X509
from pathlib import Path
from subprocess import CalledProcessError, check_output, PIPE
from urllib.parse import urljoin
from itertools import islice
from typing import Any, Dict, List, Union

try:
    # Provide assistance if adal isn't present
    import adal
except Exception:
    print('Module [adal] not found. Try [sudo apt-get install python3-adal]', file=sys.stderr)
    exit(1)


PACKAGE_KEY_IDS = ("eb3e94adbe1229cf", "0cd9fed33135ce90")
PACKAGE_EXTENSIONS = (".deb", ".rpm")


class repolib:

    @staticmethod
    def error_and_exit(msg: str):
        raise Exception(msg)
        #print(msg, file=sys.stderr)
        #exit(1)

    def __init__(self, server, port, AADClientId, AADResource, AADTenant,
                 AADAuthorityUrl, AADClientSecret=None, AADClientCertificate=None, repositoryId='',
                 AADClientCertContents=None, version=None, checkGpgKey=None, AADSubjectIssuerAuth=False):
        # Parameters are named identically to the config values, so the entire config can be passed in
        if not version:
            version = 'v2'
        if checkGpgKey:
            self.verify_gpg = checkGpgKey
        else:
            self.verify_gpg = False

        self.base_url = 'https://{0}:{1}/{2}/'.format(server, port, version)
        self.client_id = AADClientId
        self.client_certificate_contents = None
        if AADClientCertContents:
            self.client_certificate_contents = AADClientCertContents
        elif AADClientCertificate:
            self.client_certificate_path = AADClientCertificate
            try:
                with open(self.client_certificate_path, 'r') as f:
                    self.client_certificate_contents = f.read()
            except Exception as e:
                repolib.error_and_exit('Error parsing client certificate {0}: {1!s}'.format(AADClientCertificate, e))
        elif AADClientSecret:
            self.client_secret = AADClientSecret
        else:
            repolib.error_and_exit('Must provide either "AADClientSecret" or "AADClientCertificate"')

        if self.client_certificate_contents:
            # Find the leaf cert, as some CA's issue certs in reverse order
            # (CA first) which results in using the wrong thumbprint
            try:
                self.leaf_cert = self.find_leaf_cert()
                self.client_certificate_thumbprint = self._get_cert_thumbprint()
            except Exception as e:
                repolib.error_and_exit('Error processing client certificate: {0!s}'.format(e))
            # If AADSubjectIssuerAuth is true, use the leaf cert for Subject Name/Issuer Authentication; otherwise,
            # use normal (thumbprint-based) authentication
            self.sni_leaf = self.leaf_cert if AADSubjectIssuerAuth else None

        self.resource = AADResource
        self.tenant = AADTenant
        self.authority_url = urljoin(AADAuthorityUrl, AADTenant)
        self.default_repository_id = repositoryId
        self.token = None
        self.verify_ssl = True

    def disable_ssl_verification(self):
        self.verify_ssl = False

    def _get_cert_thumbprint(self) -> str:
        cert = load_certificate(FILETYPE_PEM, self.leaf_cert.encode('utf-8'))
        return cert.digest('sha1').decode('utf-8')

    def _get_token(self):
        if self.token is None:
            self.auth_context = adal.AuthenticationContext(self.authority_url)
            try:
                params = {'resource': self.resource, 'client_id': self.client_id}
                if self.client_certificate_contents is not None:
                    params['certificate'] = self.client_certificate_contents
                    params['thumbprint'] = self.client_certificate_thumbprint
                    if self.sni_leaf is not None:
                        params['public_certificate'] = self.sni_leaf
                    token_response = self.auth_context.acquire_token_with_client_certificate(**params)
                else:
                    params['client_secret'] = self.client_secret
                    token_response = self.auth_context.acquire_token_with_client_credentials(**params)

                self.token = token_response['accessToken']
            except adal.adal_error.AdalError as e:
                repolib.error_and_exit('Failed to acquire access token: {0}'.format(str(e)))
        return self.token

    def _get_headers(self, token):
        http_headers = {
            'Authorization': 'Bearer ' + token,
            'User-Agent': 'adal-python-sample',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'client-request-id': str(uuid.uuid4())
        }
        return http_headers

    def _get_url(self, path: str, params=None) -> requests.Response:
        """
        Gets the specified URL using the auth token

        :param path: relative URL to GET
        :return:        Dictionary representing keyvault response
        :raises:        ConnectionError, Exception, ValueError
        """
        msg_template = 'Connection Error while getting {0}: {1}'
        token = self._get_token()
        url = urljoin(self.base_url, path)
        http_headers = self._get_headers(token)

        try:
            resp = requests.get(url, params=params, headers=http_headers, stream=False, verify=self.verify_ssl)
        except ConnectionError as ex:
            detail = 'Error: {0!s}'.format(ex)
            raise ConnectionError(msg_template.format(url, detail))
        except requests.exceptions.SSLError as e:
            msg = 'Failed to reach API server due to SSL error {0!s}'
            repolib.error_and_exit(msg.format(e))
        if resp.status_code >= 400:
            detail = 'Status code: {0}'.format(resp.status_code)
            raise Exception(msg_template.format(url, detail))
        return resp

    def _delete_url(self, path, data=None):
        msg_template = 'Connection Error while getting {0}: {1}'
        token = self._get_token()
        url = urljoin(self.base_url, path)
        http_headers = self._get_headers(token)
        if data:
            try:
                resp = requests.delete(url, headers=http_headers, stream=False, verify=self.verify_ssl, data=json.dumps(data))
            except ConnectionError as ex:
                detail = 'Error: {0}'.format(str(ex))
                raise ConnectionError(msg_template.format(url, detail))
            except requests.exceptions.SSLError as e:
                msg = 'Failed to reach API server due to SSL error {0}'
                repolib.error_and_exit(msg.format(e))
        else:
            try:
                resp = requests.delete(url, headers=http_headers, stream=False, verify=self.verify_ssl)
            except ConnectionError as ex:
                detail = 'Error: {0}'.format(str(ex))
                raise ConnectionError(msg_template.format(url, detail))
            except requests.exceptions.SSLError as e:
                msg = 'Failed to reach API server due to SSL error {0}'
                repolib.error_and_exit(msg.format(e))
        return resp

    def _put_url(self, path, data=None):
        msg_template = 'Connection Error while getting {0}: {1}'
        token = self._get_token()
        url = urljoin(self.base_url, path)
        http_headers = self._get_headers(token)
        try:
            resp = requests.put(url, headers=http_headers, stream=False, verify=self.verify_ssl, data=json.dumps(data))
        except ConnectionError as ex:
            detail = 'Error: {0}'.format(str(ex))
            raise ConnectionError(msg_template.format(url, detail))
        except requests.exceptions.SSLError as e:
            msg = 'Failed to reach API server due to SSL error {0}'
            repolib.error_and_exit(msg.format(e))
        return resp

    def _post_url(self, path, data=None, file=None, files=None, sign=None):
        token = self._get_token()
        url = urljoin(self.base_url, path)
        http_headers = self._get_headers(token)

        if file:
            # File was specified. Need to read it.
            # Todo check file existence/contents
            # Todo combine "file" and "files" into one common code path
            del http_headers['Content-Type']
            # get file list in directory
            filename = os.path.basename(file)
            files = {'file': [filename, open(file, 'rb')]}

            try:
                resp = requests.post(url, headers=http_headers, stream=False, verify=self.verify_ssl, files=files)
            except Exception as e:
                repolib.error_and_exit(str(e))
            return resp

        elif files:
            # Files were specified. Need to read them.
            # Todo check file existence/contents
            del http_headers['Content-Type']
            # get file list in directory
            directory = [('files', open(file['fileName'], 'rb')) for file in files]
            params = {'url': url, 'headers': http_headers, 'stream': False,
                      'verify': self.verify_ssl, 'files': directory}
            if data:
                params['data'] = data
            try:
                resp = requests.post(**params)
            except Exception as e:
                repolib.error_and_exit(str(e))
            return resp

        elif data:
            try:
                resp = requests.post(url, headers=http_headers, stream=False, verify=self.verify_ssl, data=json.dumps(data))
            except Exception as e:
                repolib.error_and_exit(str(e))
            return resp

        elif sign:
            try:
                resp = requests.post(url, headers=http_headers, stream=False, verify=self.verify_ssl)
            except Exception as e:
                repolib.error_and_exit(str(e))
            return resp

    def _run_command(self, command):
        cmd_split = command.split(' ')
        try:
            res = check_output(cmd_split, stderr=PIPE)
        except CalledProcessError as e:
            output = e.stderr.decode().strip()
            raise Exception(f"{cmd_split[0]} returned {e.returncode}: {output}")
        return res.decode('utf-8')

    # Account Operations
    def list_accounts(self):
        return self._get_url('accounts')

    def add_account(self, name, appId, admin=None, prod=None):
        data = {"username": name, "appId": appId}
        if prod:
            data['isProd'] = prod
        if admin:
            data['isAdmin'] = admin
        return self._post_url('accounts', data=data)

    def delete_account_by_id(self, id):
        return self._delete_url('accounts/{0}'.format(id))

    def list_packages(self, **params: Dict[str, Any]) -> requests.Response:
        """List packages."""
        return self._get_url('packages', params=params)

    def add_package_url(self, url: str, repositoryId: str) -> requests.Response:
        """Add a package by url."""
        data = {"sourceUrl": url, "repositoryId": repositoryId}
        return self._post_url('packages', data=data)

    def upload_and_publish(
        self,
        file: Path,
        repositoryId: str,
        checkGpgKey: bool = False,
    ) -> requests.Response:
        if checkGpgKey:
            self.verify_gpg = True

        if self.verify_gpg:
            print('WARNING: Enabling GPG key verification.', file=sys.stderr)

        if self.base_url.endswith('v3/'):
            return self.upload_and_publish_batch(file, repositoryId)
        else:
            if file.suffix not in PACKAGE_EXTENSIONS:
                raise Exception(f"File {file} does not end in deb or rpm.")

            if self.verify_gpg and not self._verify_package_signature(file):
                # raise an exception when gpg key check is enabled, but the package key could not be verified.
                raise Exception(f'Could not verify gpg key of {file}.')

            # Upload package to file API, get file ID
            resp_file = self.upload_file(file)
            response_json = resp_file.json()
            if 'id' not in response_json:
                if response_json.get('status') == 'UploadRejected':
                    return resp_file
                else:
                    raise Exception('Could not interpret response from publisher service '
                                    f'{resp_file.status_code} {resp_file.text}')
            else:
                package_info = dict(fileId=response_json['id'], repositoryId=repositoryId)
                return self._post_url('packages', package_info)

    # Upload and publish a single package, or a .txt file with lists of file paths
    def upload_and_publish_batch(
        self,
        file: Path,
        repositoryId: str,
        uploadId: str = None,
    ) -> requests.Response:
        data: Dict[str, Union[str, List, None]] = {'repositoryId': repositoryId, 'uploadId': uploadId}
        # No of Files to upload in a batch from a directory
        # The http client limitation is total of 2GB of data can be transferred in a batch.
        # So ideally in the future change this to batch based on size instead of file count
        # or upload as chunks instead of batches.
        batch_size = 3

        files = self._get_pkgs_from_path(file, repositoryId)
        if not files:
            raise Exception('No verified files to submit')

        it = iter(files)
        filechunks = iter(lambda: tuple(islice(it, batch_size)), ())
        for filechunk in filechunks:
            resp_file = self._post_url('files/multi', files=filechunk, data=data)
            response_json = json.loads(resp_file.text)
            if not response_json['uploadedFiles']:
                return resp_file
            else:
                data['uploadId'] = response_json['uploadId']

        data['fileId'] = response_json['uploadId']
        data['packages'] = files
        return self._post_url('packages', data=data)

    def upload_file(self, file=None):
        return self._post_url('files', file=file)

    def check_package_id(self, id):
        return self._get_url('packages/queue/{0}'.format(id))

    def delete_package_by_id(self, id):
        print('deleting a single package id {0}'.format(id))
        # NOTE: set the migration param to true
        return self._delete_url('packages/{0}'.format(id), {"migration": True})

    def delete_packages_by_name_and_repo_id(self, names, repositoryId):
        data = {'names': names, 'repositoryId': repositoryId}
        # print('deleting multiple packages {0} for repo {1}'.format(names, repositoryId))
        return self._delete_url('packages', data=data)

    def _get_pkgs_from_path(self, path: Path, repoId: str) -> List[Dict[str, str]]:
        files = []

        if path.is_dir():
            filepaths = list(filter(lambda f: f.suffix in PACKAGE_EXTENSIONS, path.rglob("*")))
        else:
            filepaths = [path]

        for file in filepaths:
            if not self.verify_gpg or (self.verify_gpg and self._verify_package_signature(file)):
                files.append({"repositoryId": repoId, "fileName": str(file)})
        return files

    def _verify_package_signature(self, file: Path) -> bool:
        if file.suffix == '.deb':
            print(f"SIG_ERROR: Could not verify signature for {file}. Deb packages not supported.")
            return False

        res = self._run_command(f"rpm -qpi {file}")
        match = re.search(r'^Signature\s+: RSA/SHA256.*Key ID (.*)$', res, flags=re.MULTILINE)
        if match and match[1] in PACKAGE_KEY_IDS:
            return True
        else:
            print(f"SIG_ERROR: Could not determine correct signature of package {file}. Make "
                  "sure the files are signed with the PMC gpg key.")
            return False

    def _parse_certs_from_text(self) -> List[X509]:
        """
        Given one or more certificates in string/PEM form,
        parse them to a list of X509 objects
        :returns: list of one or more X509 certificate objects
        """
        lines = self.client_certificate_contents.split('\n')
        certs = []
        cert_tmp = []
        for line in lines:
            if line == '-----BEGIN CERTIFICATE-----':
                # Start capturing a new certificate
                cert_tmp = [line]
            elif line == '-----END CERTIFICATE-----':
                # Finish capturing a certificate
                cert_tmp.append(line)
                certs.append(load_certificate(FILETYPE_PEM, '\n'.join(cert_tmp).encode(encoding='utf-8')))
                cert_tmp = []
            elif cert_tmp:
                # Continue existing entry
                cert_tmp.append(line)
        return certs

    @staticmethod
    def _dump_certificate_to_text(cert: X509) -> str:
        """
        Dump an OpenSSL.crypto.X509 certificate object to its equivalent in PEM/STR form

        :param cert: The certificate to be dumped
        """
        return dump_certificate(FILETYPE_PEM, cert).decode('utf-8')

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
        issuer = None
        while len(certs) > 1:
            for cert in certs:
                if issuer is None and cert.get_issuer().CN == cert.get_subject().CN:
                    # Found root CA
                    issuer = cert.get_issuer().CN
                    last_ca = cert
                    break
                elif issuer == cert.get_issuer().CN:
                    # Found intermediary CA
                    last_ca = cert
                    break
            else:
                # Prevent looping forever if there is a break in the chain
                raise Exception('Cannot find leaf certificate due to break in chain!')
            certs.remove(last_ca)
        return certs

    def find_leaf_cert(self) -> str:
        """
        From the certificate contents that were read by the client,
        find the leaf cert.
        :returns str: leaf cert in str/PEM form
        """
        certs = self._parse_certs_from_text()
        if len(certs) == 0:
            # No certs present - must only be private key
            raise Exception('Found no leaf certificates in specified cert!')
        if len(certs) > 1:
            # Cert chain is present - remove root/intermediary CA's.
            certs = repolib._remove_cas_from_chain(certs)
        # Only one cert present - must be the leaf cert
        return repolib._dump_certificate_to_text(certs[0])

    # Repository Operations
    def list_repositories(self, name=None, type=None, username=None, release=None, sign=None, state=None):
        params = {}

        if name:
            params['url'] = name
        if type:
            params['type'] = type
        if username:
            params['username'] = username
        if release:
            params['release'] = release
        if sign:
            params['prss'] = sign
        if state:
            params['state'] = state

        return self._get_url('repositories', params=params)

    def list_local_deb_repositories(self):
        return self._get_url('repositories/local')

    def list_published_deb_repositories(self, name, release):
        params = {"url": name, "distribution": release}
        if name:
            params['url'] = name
        if release:
            params['release'] = release
        return self._get_url('admin/repositories/publish', params=params)

    def check_publish_request_status(self, id):
        return self._get_url('publishingRequest/{0}'.format(id))

    def check_repo_id(self, id):
        return self._get_url('repositories/{0}'.format(id))

    def add_repository(self, name, repo_type, editors, component=None, release=None, legacy_sign=False):
        data = {"url": name, "editors": editors, "type": repo_type}
        if release:
            data['distribution'] = release
        if component:
            data['component'] = component
        # Disable PRSS signing if legacy_sign is True
        data['prss'] = not legacy_sign
        return self._post_url('repositories', data=data)

    def is_response_success(self, response: requests.Response) -> bool:
        if response is None:
            return False
        return response.status_code < 400

    def repair_repositories(self) -> int:
        res = self.list_repositories()
        if not self.is_response_success(res):
            print('Failed to acquire list of repos', file=sys.stderr)
            return 1
        res_json = json.loads(res.text)
        repos_to_repair = {repo['url']: repo['id'] for repo in res_json if repo.get('state') == 'SignError'}
        if not repos_to_repair:
            print('All repos are healthy')
            return 0
        fail_count = 0
        sleep_time = 0
        for name, id in repos_to_repair.items():
            if sleep_time > 0:
                # Sleep for a minute between operations
                time.sleep(sleep_time)
            else:
                sleep_time = 60  # Sleep before subsequent operations
            print('Repairing {}'.format(name))
            res = self.publish_repository(id)
            if not self.is_response_success(res):
                print('Failed to repair {}'.format(name), file=sys.stderr)
                fail_count += 1

        repaired_count = len(repos_to_repair) - fail_count
        print('Summary: Repaired [{}] Failed [{}])'.format(repaired_count, fail_count))
        return fail_count

    def publish_repository(self, id):
        return self._post_url('repositories/{0}'.format(id), sign=True)

    def stage_repository(self, id):
        data = {'repositoryIds': [id]}
        return self._post_url('repositories/stage', data=data)

    def set_prod_repository_editors(self):
        return self._post_url('repositories/prodeditors')

    def delete_repository(self, id):
        return self._delete_url('repositories/publish/{0}'.format(id))
