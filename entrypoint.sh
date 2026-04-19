#!/bin/bash

USER_ID=${PUID:-1000}
GROUP_ID=${PGID:-1000}

echo "Starting with UID : $USER_ID, GID: $GROUP_ID"

if [ ! -f /app/data/config.json ]; then
    echo "Creating config.json from template..."
    cp /app/config.json.EXAMPLE /app/data/config.json
else
    echo "Updating config.json with any new fields from template..."
    tmp=$(mktemp)
    jq -s '.[0] * .[1]' /app/config.json.EXAMPLE /app/data/config.json > "$tmp" && mv "$tmp" /app/data/config.json
fi

chown -R $USER_ID:$GROUP_ID /app/data

umask 002

exec gosu $USER_ID:$GROUP_ID "$@"