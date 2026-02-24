#!/bin/bash
# myip.sh - Show public IP and location info

DATA=$(curl -s https://ipinfo.io/json)

IP=$(echo "$DATA" | grep '"ip"' | cut -d '"' -f4)
CITY=$(echo "$DATA" | grep '"city"' | cut -d '"' -f4)
REGION=$(echo "$DATA" | grep '"region"' | cut -d '"' -f4)
COUNTRY=$(echo "$DATA" | grep '"country"' | cut -d '"' -f4)

echo "Public IP : $IP"
echo "Location  : $CITY, $REGION, $COUNTRY"