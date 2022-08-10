import datetime
import json
import logging
import more_itertools

import azure.functions as func
from shared_code.utils import (get_status_msg, load_ca, get_apt_filter, get_yum_filter,
                               check_and_add_task)
from repoaudit.utils import get_repo_urls


def main(
    mytimer: func.TimerRequest,
    repositorystatus: str,
    msg: func.Out[func.QueueMessage],
    msgresultsqueue: func.Out[func.QueueMessage]
) -> None:
    """
    Azure function that generates a list of apt and yum repositories and adds them to
    repo-request-queue to be checked by check_repo. Apt repositories are further
    divided by distribution. Only repos/dists that have been recently updated or have
    stale status are queued to be checked. Also adds two filter lists, for apt and
    yum repos, to the results-queue to filter deleted repos.
    """

    current_status = json.loads(repositorystatus)

    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if mytimer.past_due:
        logging.warning('The timer is past due!')

    logging.info(f'generate_apt ran at {utc_timestamp}')

    with load_ca() as verify:
        apt_urls = get_repo_urls("https://packages.microsoft.com/repos/", verify=verify)
        apt_filter = get_apt_filter(apt_urls, verify=verify)
        yum_urls = get_repo_urls("https://packages.microsoft.com/yumrepos/", verify=verify)
        yum_filter = get_yum_filter(yum_urls)

    # add apt repos/dists to check
    apt_tasks = []
    for repo, dists in apt_filter.items():
        if dists:
            for dist in dists:
                task = {"type": "apt", "repo": repo, "dists": [dist]}
                check_and_add_task(task, apt_tasks, current_status)
        else:
            task = {"type": "apt", "repo": repo}
            check_and_add_task(task, apt_tasks, current_status)

    # add yum repos to check
    yum_tasks = []
    for repo in yum_urls:
        task = {"type": "yum", "repo": repo}
        check_and_add_task(task, yum_tasks, current_status)

    tasks = list(more_itertools.roundrobin(apt_tasks, yum_tasks))

    # create filter updates for results-queue
    filters = [
        get_status_msg(apt_filter, "apt-list"),
        get_status_msg(yum_filter, "yum-list")
    ]

    msg.set(tasks)
    msgresultsqueue.set(filters)
