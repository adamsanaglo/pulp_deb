#!/usr/bin/sh
# This helper script will only work in the dev environment because it requires direct access to the
# database. The intent is to help you "become" different types of accounts so that you can get
# through the RBAC restrictions and actually test your code.
usage="Usage: update_role.sh <Account_Admin|Repo_Admin|Package_Admin|Publisher> [--create]"

if [ $# -eq 0 ]
 then
   echo $usage
   exit 1
fi

# Validate the role.
case "$1" in
  Account_Admin) ;;
  Repo_Admin) ;;
  Package_Admin) ;;
  Publisher) ;;
  *) echo $usage; exit 1;;
esac

# This is the oid of the principal that we are using for our dev setup. If the principal changes
# we'd have to update this.
account_id="1334b698-bee4-4556-ae45-a5e7b5698504"

if [ "$2" = "--create" ]
 then
   docker exec -i db psql -U pmcserver -c "delete from account where id = '$account_id'"
   docker exec -i db psql -U pmcserver -c "insert into account (id, name, role, icm_service, icm_team, contact_email, is_enabled, created_at, last_edited) values ('$account_id', 'dev', '$1', 'dev', 'dev', 'dev@user.com', 't', now(), now())"
 else
   docker exec -i db psql -U pmcserver -c "update account set role = '$1' where id = '$account_id'"
fi