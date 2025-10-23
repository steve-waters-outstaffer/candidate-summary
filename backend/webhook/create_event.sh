# 1. Configuration (Replace placeholders with your actual values)
RCRM_API_TOKEN="ngglqbmrYAVJwvqsDv5vI-WL-UCM1Brsk8sqpG5kMPOP4ImAmBDW1oiuFAa7kl-D7sO6PAEGEod0LmzTcgehg18xNzUwNDkyMjE0Onw6cHJvZHVjdGlvbg=="
WEBHOOK_URL="https://recruitcrm-webhook-listener-hdg54dp7ga-uc.a.run.app"
EVENT_NAME="candidate.hiringstage.updated"

# 2. JSON Payload for the Subscription
SUBSCRIPTION_PAYLOAD='{
    "target_url": "'"$WEBHOOK_URL"'",
    "event": "'"$EVENT_NAME"'"
}'

# 3. Execute the cURL POST request
curl -X POST "https://api.recruitcrm.io/v1/subscriptions" \
     -H "Authorization: Bearer $RCRM_API_TOKEN" \
     -H "Content-Type: application/json" \
     -d "$SUBSCRIPTION_PAYLOAD"