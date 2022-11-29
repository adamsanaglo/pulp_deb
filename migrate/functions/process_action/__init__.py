import json
import logging

import azure.functions as func

# from process_action.vcurrent import remove_vcurrent_package
from process_action.vnext import remove_vnext_packages, trigger_vnext_sync
from schemas import Action, ActionType, SourceType


def main(msg: func.ServiceBusMessage):
    msg_json = json.loads(msg.get_body().decode("utf-8"))
    action = Action(**msg_json)

    action.translate_repo_name()
    logging.info(f"[PROCESS]: {action}.")

    if action.source == SourceType.vcurrent:
        if action.action_type == ActionType.add:
            trigger_vnext_sync(action.repo_name)
        elif action.action_type == ActionType.remove:
            remove_vnext_packages(action)
    elif action.source == SourceType.vnext:
        if action.action_type == ActionType.remove:
            # TODO: https://msazure.visualstudio.com/One/_workitems/edit/16220041
            # remove_vcurrent_package(action)
            pass
        elif action.action_type == ActionType.add:
            # we don't add packages to vcurrent
            raise NotImplementedError
