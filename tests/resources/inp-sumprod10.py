#!/usr/bin/env python3

s = 0
p = 1
for i in range(1, 11):
    s += i
    p *= i

print(f'sum: {s}')
print(f'prod: {p}')
