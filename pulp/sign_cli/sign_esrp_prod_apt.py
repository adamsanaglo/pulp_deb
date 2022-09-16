#!/usr/bin/python3
# This script will run in Pulp container, so deliberately use minimal dependencies

import sys

from signlib import parse_parameters, sign_content

file_to_sign = parse_parameters(sys.argv)
print(sign_content(file_to_sign, 'esrp_prod', apt=True))
