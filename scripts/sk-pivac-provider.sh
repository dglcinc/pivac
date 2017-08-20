#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
COMMAND="python $DIR/sk-pivac-provider.py $@"

exec -a pivac $DIR/sk-provider.sh $COMMAND &
