#!/usr/bin/env python3
import getopt
import sys
import uuid
from datetime import datetime
from typing import List

from app.core.config import settings
from app.core.models import Account, Role


def sign(account: Account) -> None:
    account.sign()
    print(f"{account.id},{account.created_at},{account.last_edited},{account.signature}")


def _get_account_from_args(argv: List[str]) -> Account:
    arg_help = (
        f"{argv[0]} --id <id> --oid <oid> --role <role> --name <name> --email"
        "<contact-email> --service <icm-service> --team <icm-team> --enabled <is-enabled>"
        "--created-at <created-at> --last-edited <last-edited>"
    )

    try:
        opts, _ = getopt.getopt(
            argv[1:],
            "hi:o:r:n:e:s:t:b:c:l:",
            [
                "help",
                "id=",
                "oid=",
                "role=",
                "name=",
                "email=",
                "service=",
                "team=",
                "enabled=",
                "created-at=",
                "last-edited=",
            ],
        )
    except Exception:
        print(arg_help)
        sys.exit(-1)

    account = Account()
    account.oid = uuid.UUID(settings.ADMIN_ACCOUNT_CLIENT_ID)
    account.name = "dev"
    account.is_enabled = True
    account.role = Role.Account_Admin
    account.icm_service = "dev"
    account.icm_team = "dev"
    account.contact_email = "dev@user.com"

    datetime_format = "%Y-%m-%d %H:%M:%S.%f"

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print(arg_help)  # print the help message
            sys.exit(-1)
        elif opt in ("-i", "--id"):
            try:
                account.id = uuid.UUID(arg)
            except Exception:
                raise Exception(f"Invalid Id: {arg}")
        elif opt in ("-o", "--oid"):
            account.oid = uuid.UUID(arg)
        elif opt in ("-r", "--role"):
            account.role = Role(arg)
        elif opt in ("-n", "--name"):
            account.name = arg
        elif opt in ("-e", "--email"):
            account.contact_email = arg
        elif opt in ("-s", "--service"):
            account.icm_service = arg
        elif opt in ("-t", "--team"):
            account.icm_team = arg
        elif opt in ("-b", "--enabled"):
            account.is_enabled = True if arg == "t" else False
        elif opt in ("-c", "--created-at"):
            account.created_at = datetime.strptime(arg, datetime_format)
        elif opt in ("-l", "--last-edited"):
            account.last_edited = datetime.strptime(arg, datetime_format)

    return account


if __name__ == "__main__":
    account = _get_account_from_args(sys.argv)
    sign(account)
