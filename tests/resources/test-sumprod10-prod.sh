#! /bin/bash
python3 $1 2>&1 | grep -q "prod: 3628800"
