#!/bin/bash
set -e

# Wait for Authentik to be fully ready
echo "Waiting for Authentik API to be ready..."
for i in {1..60}; do
  if timeout 2 curl -s -k https://auth.zavia.lan/api/v3/admin/versions/ > /dev/null 2>&1; then
    echo "Authentik API is ready"
    break
  fi
  echo "Attempt $i/60: Authentik not ready yet, waiting..."
  sleep 2
done

# Get initial auth token
echo "Getting Authentik admin token..."
ADMIN_TOKEN=$(timeout 10 curl -s -k -X POST https://auth.zavia.lan/api/v3/admin/login/create \
  -H "Content-Type: application/json" \
  -d '{"username":"akadmin","password":"akadmin"}' | grep -o '"access":"[^"]*' | cut -d'"' -f4)

if [ -z "$ADMIN_TOKEN" ]; then
  echo "Failed to get admin token"
  exit 1
fi

echo "Got admin token"

# Create UNS OAuth2 Provider
echo "Creating UNS OAuth2 provider..."
PROVIDER_RESPONSE=$(curl -s -k -X POST https://auth.zavia.lan/api/v3/providers/oauth2/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "UNS OAuth2 Provider",
    "client_id": "Qp5tqrUExqPzZfOuyiO8ptGk6hbkmSEJhkUF6jms",
    "client_secret": "qmqm5IOhW4pHCcEAJayJoKfCNIvzV9qBkGK5WqJskNxa85miczMHXhkYOXCd2DniI5JZmedGMirwiJuoBfbn33z07eCQeh592xqoSY6aqTZCggaEQZ3kOejw4nhjsEiS",
    "redirect_uris": "https://uns.zavia.lan/callback",
    "scopes": "openid profile email",
    "authorization_flow": null,
    "oidc_jwks_url": "https://auth.zavia.lan/application/o/uns/jwks.json/"
  }')

echo "Provider response: $PROVIDER_RESPONSE"
PROVIDER_ID=$(echo "$PROVIDER_RESPONSE" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)

if [ -z "$PROVIDER_ID" ]; then
  echo "Failed to create provider"
  exit 1
fi

echo "Created provider with ID: $PROVIDER_ID"

# Create UNS Application
echo "Creating UNS application..."
APP_RESPONSE=$(curl -s -k -X POST https://auth.zavia.lan/api/v3/core/applications/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"UNS\",
    \"slug\": \"uns\",
    \"provider\": $PROVIDER_ID,
    \"meta_description\": \"Unified Namespace System\",
    \"open_in_new_tab\": true
  }")

echo "Application response: $APP_RESPONSE"

if echo "$APP_RESPONSE" | grep -q '"slug":"uns"'; then
  echo "UNS OAuth2 application created successfully!"
else
  echo "Failed to create application"
  exit 1
fi

echo "Setup complete!"
