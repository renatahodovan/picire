#! /bin/bash
python $1 2>&1 | grep -q "prod: 3628800"
