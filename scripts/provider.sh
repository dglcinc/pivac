#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
COMMAND="$@"
CMD_PID=0

stop()
{
#    echo "stopping..."
    kill $CMD_PID
    exit 0
}
restart()
{
#    echo "restarting..."
    kill $CMD_PID
}

trap stop 2 3 9 15
trap restart 1

while true
  do
    $COMMAND &
    CMD_PID=$!
    wait
done
