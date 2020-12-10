#! /bin/bash
python $(dirname $0)/sut-json-load.py $1 2>&1 | grep -q -E "Expecting property name|Expecting object"
