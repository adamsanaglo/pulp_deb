#!/usr/bin/python3
# This script will run in Pulp container, so deliberately use minimal dependencies

import sys
from signlib import sign_content, parse_parameters

file_to_sign = parse_parameters(sys.argv)
print(sign_content(file_to_sign, 'esrp_prod'))