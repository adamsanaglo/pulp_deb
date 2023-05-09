#!/usr/bin/bash
# This helper script will only work in the dev environment because it requires direct access to the
# database. It allows us to automatically create the initial dev-environment accounts.
usage="Usage: create_account.sh <Account_Admin|Repo_Admin|Package_Admin|Publisher|Migration> <enterprise_application_oid>"

if [ $# -ne 2 ]; then
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

docker_container_state=$(docker container inspect pmcserver | jq -r .[].State.Status)
sign_poetry_command='unset VIRTUAL_ENV && cd .. && PULP_HOST="http://localhost:8080" POSTGRES_SERVER="127.0.0.1" poetry run python3 deployment/sign_initial_account.py --role "$1" --name "$1" --oid "$2"'
sign_docker_command='docker exec -i pmcserver python3 sign_initial_account.py --role "$1" --name "$1" --oid "$2"'

# Deleting the old account with the same oid if it exists.
docker exec -i db psql -U pmcserver -c "delete from account where oid = '$2'"
# Initializing signed account fields.
if [ "$docker_container_state" = "running" ]
then
  IFS=',' read -r id created_at last_edited signature <<<$(eval "$sign_docker_command")
else
  IFS=',' read -r id created_at last_edited signature <<<$(eval "$sign_poetry_command")
fi
# Insert the signed account into db.
docker exec -i db psql -U pmcserver -c "insert into account (id, oid, name, role, icm_service, icm_team, contact_email, is_enabled, created_at, last_edited, signature) values ('$id', '$2', '$1', '$1', 'dev', 'dev', 'dev@user.com', 't', '$created_at', '$last_edited', '$signature')"
