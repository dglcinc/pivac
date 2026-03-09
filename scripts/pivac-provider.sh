#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
COMMAND="/home/pi/pivac-venv/bin/python3 $DIR/pivac-provider.py $@"

exec $DIR/provider.sh $COMMAND &
