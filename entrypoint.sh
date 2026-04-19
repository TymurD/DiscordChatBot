#!/bin/bash

if [ ! -f /app/data/config.json ]; then
    echo "Creating config.json from template..."
    cp /app/config.json.EXAMPLE /app/data/config.json
else
    echo "Updating config.json with any new fields from template..."
    tmp=$(mktemp)
    jq -s '.[0] * .[1]' /app/config.json.EXAMPLE /app/data/config.json > "$tmp" && mv "$tmp" /app/data/config.json
fi

exec "$@"