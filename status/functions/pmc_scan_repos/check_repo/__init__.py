import json
import logging

from shared_code.utils import (load_ca, load_gpg, log_message, get_repo_from_msg,
                               get_status_msg, get_dists_from_msg)
from repoaudit.utils import RepoErrors
from repoaudit.apt import check_apt_repo
from repoaudit.yum import check_yum_repo

import azure.functions as func


def main(
    msg: func.QueueMessage,
    inputblobpubkeys: str,
    msgout: func.Out[str]
) -> None:
    """
    Azure function that takes as input a message from repo-request-queue with
    either an apt or yum repository url, and the key url's to check signatures.
    This will check if the repository is healthy according to the repoaudit
    module and output the status to the results-queue.
    """
    log_message(msg)

    type, repo = get_repo_from_msg(msg)
    logging.info(f'Processing repo: {repo}, with type: {type}')

    pubkeys = json.loads(inputblobpubkeys)
    logging.info(f"Using the public keys: {pubkeys}")

    errors = RepoErrors()

    with load_ca() as verify:
        with load_gpg(pubkeys, verify=verify) as gpg:
            if type == "apt":
                dists = get_dists_from_msg(msg)
                logging.info(f"Checking dists: {dists}")
                check_apt_repo(repo, dists, gpg, errors, verify=verify)
            elif type == "yum":
                check_yum_repo(repo, gpg, errors, verify=verify)
            else:
                logging.error(f"{repo} is of unknown repo type {type}")
                return

    logging.info(errors.get_json())
    msgout.set(get_status_msg(errors.errors, type))
