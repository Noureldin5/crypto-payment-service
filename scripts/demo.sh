#!/usr/bin/env bash
# Demo for the midterm. Usage: ./scripts/demo.sh [http://SERVER_IP:8000]
BASE=${1:-http://localhost:8000}
KEY="X-API-Key: shop-secret"
JSON="Content-Type: application/json"

say() { echo; echo "=== $1 ==="; }

say "1. Successful payment (client 1 has 5 BTC)"
RESP=$(curl -s -X POST "$BASE/payments" -H "$KEY" -H "$JSON" -H "Idempotency-Key: demo-$(date +%s)" \
  -d '{"client_id":"1","amount":"0.5","description":"Order #1042"}')
echo "$RESP"
ID=$(echo "$RESP" | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')

say "2. Not enough money (client 2 has 0.1 BTC)"
curl -s -X POST "$BASE/payments" -H "$KEY" -H "$JSON" -d '{"client_id":"2","amount":"1"}'; echo

say "3. Client is blocked in ABC (client 3)"
curl -s -X POST "$BASE/payments" -H "$KEY" -H "$JSON" -d '{"client_id":"3","amount":"0.1"}'; echo

say "4. Client has no wallet (client 4)"
curl -s -X POST "$BASE/payments" -H "$KEY" -H "$JSON" -d '{"client_id":"4","amount":"0.1"}'; echo

say "5. Wrong API key -> 401"
curl -s -X POST "$BASE/payments" -H "X-API-Key: wrong" -H "$JSON" -d '{"client_id":"1","amount":"0.1"}'; echo

say "6. Waiting for a block to confirm payment 1 (miner runs every 10s)..."
sleep 12
curl -s "$BASE/payments/$ID" -H "$KEY"; echo
