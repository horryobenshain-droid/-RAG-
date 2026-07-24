#!/bin/sh
set -eu

password_file="/run/rag-secrets/auth_password"
auth_user="${RAG_AUTH_USER:-admin}"

if ! printf '%s' "$auth_user" | grep -Eq '^[A-Za-z0-9._-]{1,64}$'; then
    echo "RAG_AUTH_USER may only contain letters, numbers, dot, underscore, and hyphen." >&2
    exit 1
fi

if [ ! -s "$password_file" ]; then
    echo "Missing deployment secret: deploy/secrets/auth_password" >&2
    echo "Create it before starting the Compose stack." >&2
    exit 1
fi

auth_password="$(cat "$password_file")"
if [ "${#auth_password}" -lt 12 ]; then
    echo "The deployment password must contain at least 12 characters." >&2
    exit 1
fi

htpasswd -bcB /etc/nginx/.htpasswd "$auth_user" "$auth_password" >/dev/null
chown root:nginx /etc/nginx/.htpasswd
chmod 0640 /etc/nginx/.htpasswd
unset auth_password
