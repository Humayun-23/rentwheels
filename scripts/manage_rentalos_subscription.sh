#!/bin/bash

# manage_rentalos_subscription.sh
# Manually activates or deactivates RentalOS access for a given shop using psql.

set -e

if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <activate|deactivate> <shop_id> [days]"
    echo "Example: $0 activate 1 30"
    echo "Example: $0 deactivate 1"
    exit 1
fi

ACTION=$1
SHOP_ID=$2
DAYS=${3:-30}

# Source the .env file to get DATABASE_URL
if [ -f "../.env" ]; then
    export $(grep -v '^#' ../.env | xargs)
elif [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
else
    echo "Error: .env file not found."
    exit 1
fi

if [ -z "$DATABASE_URL" ]; then
    echo "Error: DATABASE_URL is not set in .env."
    exit 1
fi

if [ "$ACTION" = "activate" ]; then
    echo "Activating RentalOS for shop $SHOP_ID for $DAYS days..."
    psql "$DATABASE_URL" -c "UPDATE shops SET rentalos_subscription_status = 'active', rentalos_subscription_end_date = NOW() + INTERVAL '$DAYS days' WHERE id = $SHOP_ID;"
    echo "Shop $SHOP_ID is now active."
elif [ "$ACTION" = "deactivate" ]; then
    echo "Deactivating RentalOS for shop $SHOP_ID..."
    psql "$DATABASE_URL" -c "UPDATE shops SET rentalos_subscription_status = 'inactive', rentalos_subscription_end_date = NULL WHERE id = $SHOP_ID;"
    echo "Shop $SHOP_ID is now inactive."
else
    echo "Invalid action: $ACTION. Use 'activate' or 'deactivate'."
    exit 1
fi
