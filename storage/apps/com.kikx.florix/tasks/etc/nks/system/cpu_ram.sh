#!/bin/bash

CPU=$(top -bn1 | grep "Cpu(s)" | awk '{print 100 - $8}')
RAM=$(free | grep Mem | awk '{print $3/$2 * 100.0}')

if (( $(echo "$CPU > 80" | bc -l) )); then
  echo "High CPU usage: $CPU%"
fi

if (( $(echo "$RAM > 80" | bc -l) )); then
  echo "High RAM usage: $RAM%"
fi