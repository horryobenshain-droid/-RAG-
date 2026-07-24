#!/bin/sh
set -eu

action="${1:-start}"
project_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
production_env="$project_root/.env.production"
password_file="$project_root/deploy/secrets/auth_password"

compose() {
    docker compose --env-file "$production_env" "$@"
}

initialize_deployment_files() {
    if [ ! -f "$production_env" ]; then
        cp "$project_root/.env.production.example" "$production_env"
        echo "Created .env.production. Review model and port settings before public use."
    fi

    if [ ! -f "$password_file" ]; then
        mkdir -p "$(dirname -- "$password_file")"
        printf 'Create the RAG Studio password (at least 12 characters): '
        stty -echo
        IFS= read -r auth_password
        stty echo
        printf '\n'
        if [ "${#auth_password}" -lt 12 ]; then
            echo "The deployment password must contain at least 12 characters." >&2
            exit 1
        fi
        umask 077
        printf '%s' "$auth_password" > "$password_file"
        unset auth_password
        echo "Created deploy/secrets/auth_password."
    fi
}

if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is not installed or is not available in PATH." >&2
    exit 1
fi

cd "$project_root"

case "$action" in
    start)
        initialize_deployment_files
        compose up --detach --build
        compose ps
        echo "RAG Studio: http://127.0.0.1:8080"
        ;;
    stop)
        compose down
        ;;
    restart)
        initialize_deployment_files
        compose up --detach --build --force-recreate
        compose ps
        ;;
    status)
        compose ps
        ;;
    logs)
        compose logs --follow --tail 200
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}" >&2
        exit 2
        ;;
esac
