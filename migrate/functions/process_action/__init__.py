import json
import logging
from itertools import groupby

import azure.functions as func

from process_action.vcurrent import remove_vcurrent_package
from process_action.vnext import remove_vnext_packages, trigger_vnext_sync
from schemas import Action, ActionType, SourceType


def process_vcurrent_actions(actions):
    """Process an actions from vcurrent."""
    errors = []

    if actions[0].action_type == ActionType.add:
        logging.info(f"[ADD]: {actions[0]}.")
        try:
            trigger_vnext_sync(actions[0].repo_name)
        except Exception as e:
            logging.exception(e)
            errors.append(e)
    else:
        packages = [action.package for action in actions]
        logging.info(
            f"[REMOVE]: {actions[0].repo_name} {actions[0].release} - {len(packages)} packages."
        )
        try:
            errors = remove_vnext_packages(
                actions[0].repo_name, actions[0].release, packages
            )
        except Exception as e:
            logging.exception(e)
            errors.append(e)

    return errors


def process_vnext_actions(actions):
    """Process an actions from vnext."""

    # TODO: handle this in batches

    errors = []

    for action in actions:
        if action.action_type == ActionType.remove:
            try:
                logging.info(f"[REMOVE]: {action}.")
                remove_vcurrent_package(action)
            except Exception as e:
                logging.exception(e)
                errors.append(str(e))
        elif action.action_type == ActionType.add:
            # we don't add packages to vcurrent
            errors.add(f"Received action to add package to vcurrent: {action}")

    return errors


def main(msg: func.ServiceBusMessage):
    logging.info(f"[PROCESS] processing {len(msg)} messages.")

    actions = []
    errors = []

    for msg_item in msg:
        try:
            msg_json = json.loads(msg_item.get_body().decode("utf-8"))
            action = Action(**msg_json)
            action.translate_repo_name()
            actions.append(action)
        except Exception as e:
            logging.exception(e)
            errors.append(f"Failed to parse message: {msg_item}")

    batches = [
        list(grp)
        for k, grp in groupby(actions, lambda a: (a.source, a.repo_name, a.action_type))
    ]

    for batch in batches:
        if batch[0].source == SourceType.vnext:
            errors = process_vnext_actions(batch)
        else:
            errors = process_vcurrent_actions(batch)

    if errors:
        raise Exception(f"[PROCESS] Error processing actions: {errors}")

    logging.info(f"[PROCESS] finished processing {len(msg)} messages.")
