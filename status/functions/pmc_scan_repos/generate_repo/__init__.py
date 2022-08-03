import datetime
import json
import logging
import more_itertools

import azure.functions as func
from shared_code.utils import get_status_msg, load_ca, get_apt_filter, get_yum_filter
from repoaudit.utils import get_repo_urls


def main(
    mytimer: func.TimerRequest,
    msg: func.Out[func.QueueMessage],
    msgresultsqueue: func.Out[func.QueueMessage]
) -> None:
    """
    Azure function that generates a list of apt and yum repositories and adds them to
    repo-request-queue to be checked by check_repo. Apt repositories are further
    divided by distribution. Also adds two filter list, for apt and yum repos, to the
    results-queue to filter deleted repos.
    """
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
                apt_tasks.append(json.dumps(task))
        else:
            task = {"type": "apt", "repo": repo}
            apt_tasks.append(json.dumps(task))

    # add yum repos to check
    yum_tasks = []
    for repo in yum_urls:
        task = {"type": "yum", "repo": repo}
        yum_tasks.append(json.dumps(task))

    tasks = list(more_itertools.roundrobin(apt_tasks, yum_tasks))

    # create filter updates for results-queue
    filters = [
        get_status_msg(apt_filter, "apt-list"),
        get_status_msg(yum_filter, "yum-list")
    ]

    msg.set(tasks)
    msgresultsqueue.set(filters)
