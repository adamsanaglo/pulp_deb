import json
import logging

import azure.functions as func
from schemas import Action, SourceType, ActionType, RepoType

from process_action.vnext import remove_vnext_package, trigger_vnext_sync
from process_action.vcurrent import remove_vcurrent_package


def main(msg: func.ServiceBusMessage):
    msg_json = json.loads(msg.get_body().decode("utf-8"))
    action = Action(**msg_json)

    logging.info(f"[PROCESS]: {action}.")

    if action.source == SourceType.vcurrent:
        # append repo type to name for vnext repos
        if action.repo_type == RepoType.apt:
            action.repo_name = f"{action.repo_name}-apt"
        if action.repo_type == RepoType.yum:
            action.repo_name = f"{action.repo_name}-yum"

        if action.action_type == ActionType.add:
            trigger_vnext_sync(action.repo_name)
        elif action.action_type == ActionType.remove:
            remove_vnext_package(action)
    elif action.source == SourceType.vnext:
        # remove repo type from name
        if action.repo_type == RepoType.apt:
            action.repo_name = action.repo_name.rstrip("-apt")
        if action.repo_type == RepoType.yum:
            action.repo_name = action.repo_name.rstrip("-yum")

        if action.action_type == ActionType.remove:
            remove_vcurrent_package(action)
        elif action.action_type == ActionType.add:
            # we don't add packages to vcurrent
            raise NotImplementedError
