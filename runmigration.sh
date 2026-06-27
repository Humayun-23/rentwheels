#!/bin/bash

echo "Running Alembic migrations on gopanda-backend..."

az containerapp exec \
  --name gopanda-backend \
  --resource-group Gopanda \
  --command "alembic upgrade head"

echo "Migration command finished!"
