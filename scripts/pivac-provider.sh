#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
COMMAND="python $DIR/pivac-provider.py $@"

exec $DIR/provider.sh $COMMAND &
