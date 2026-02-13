#!/bin/bash

ping -c 1 8.8.8.8 > /dev/null 2>&1

if [ $? -eq 0 ]; then
  echo "Internet is connected"
else
  echo "No internet connection"
fi