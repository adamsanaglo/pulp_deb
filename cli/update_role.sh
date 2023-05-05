#!/usr/bin/bash
# This helper script will only work in the dev environment because it requires direct access to the
# database. The intent is to help you "become" different types of accounts so that you can get
# through the RBAC restrictions and actually test your code.
usage="Usage: update_role.sh <Account_Admin|Repo_Admin|Package_Admin|Publisher|Migration> [--create]"

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
  Migration) ;;
  *) echo $usage; exit 1;;
esac

# This is the oid of the principal that we are using for our dev setup. If the principal changes
# we'd have to update this.
account_oid="1334b698-bee4-4556-ae45-a5e7b5698504"
docker_container_state=$(docker container inspect pmcserver | jq -r .[].State.Status)
sign_poetry_command='unset VIRTUAL_ENV && cd ../server && PULP_HOST="http://localhost:8080" POSTGRES_SERVER="127.0.0.1" poetry run python3 deployment/sign_initial_account.py'
sign_docker_command='docker exec -i pmcserver python3 sign_initial_account.py --role "$1"'

if [ "$2" = "--create" ]
 then
   # Deleting the old account with the same oid if it exists.
   docker exec -i db psql -U pmcserver -c "delete from account where oid = '$account_oid'"
   # Initializing signed account fields.
   if [ "$docker_container_state" = "running" ]
   then
     IFS=',' read -r id created_at last_edited signature <<<$(eval "$sign_docker_command")
   else
     IFS=',' read -r id created_at last_edited signature <<<$(eval "$sign_poetry_command")
   fi
   # Insert the signed account into db.
   docker exec -i db psql -U pmcserver -c "insert into account (id, oid, name, role, icm_service, icm_team, contact_email, is_enabled, created_at, last_edited, signature) values ('$id', '$account_oid', 'dev', '$1', 'dev', 'dev', 'dev@user.com', 't', '$created_at', '$last_edited', '$signature')"
 else
   # Read all the fields from db to construct the Account that will be signed.
   IFS=',' read -r id name enabled service team email created_at last_edited <<<$(docker exec -i db psql -U pmcserver -t --csv -c "select id, name, is_enabled, icm_service, icm_team, contact_email, created_at, last_edited from account where oid = '$account_oid'")
   # Pass the account fields to the Python signing script.
   if [ "$docker_container_state" = "running" ]
   then
     IFS=',' read -r id created_at last_edited signature <<<$(eval "$sign_docker_command" --id "$id" --name "$name" --enabled "$enabled" --service "$service" --team "$team" --email '"$email"' --created-at '"$created_at"' --last-edited '"$last_edited"')
   else
     IFS=',' read -r id created_at last_edited signature <<<$(eval "$sign_poetry_command" --id "$id" --name "$name" --enabled "$enabled" --service "$service" --team "$team" --email '"$email"' --role "$1" --created-at '"$created_at"' --last-edited '"$last_edited"')
   fi
   # Update the account table entry with the new role and signature.
   docker exec -i db psql -U pmcserver -c "update account set role = '$1', signature = '$signature' where oid = '$account_oid'"
fi
