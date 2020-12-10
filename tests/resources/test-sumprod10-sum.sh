#! /bin/bash
python $1 2>&1 | grep -q "sum: 55"
