#!/bin/bash

echo "===== SYSTEM HEALTH REPORT ====="
echo "Date: $(date)"
echo

echo "---- Uptime ----"
uptime
echo

echo "---- Memory Usage ----"
free -h
echo

echo "---- Disk Usage ----"
df -h
echo

echo "---- Top 5 Processes ----"
ps aux --sort=-%mem | head -n 6