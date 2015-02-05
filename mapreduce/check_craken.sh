#!/bin/bash

check=$(ps -ef | grep -i "kraken" | grep -v "grep" | wc -l)

if [ "$check" -lt 1 ]
then
    echo "Service Died.... Restarting"
    /home/tkuben/crawler/mapreduce/run_kraken.sh >> /home/tkuben/crawler/mapreduce/output
else
    echo "Service still alive"
fi
