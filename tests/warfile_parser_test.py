#!/usr/bin/env python

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from tomcat import parse_warfile

test_data = [
    ('app1.war', ('/app1', '/app1', None) ),
    ('/tmp/app1.war', ('/app1', '/app1', None) ),
    ('app1##1.0.1.war', ('/app1##1.0.1', '/app1', '1.0.1') ),
    ('/tmp/app1##1.0.1.war', ('/app1##1.0.1', '/app1', '1.0.1') )
]

for fname, expected_value in test_data:
    result = parse_warfile(fname)
    try:
        assert result == expected_value
    except AssertionError:
        print "ERROR: parse_warfile({0}) \n\t      is '{1}' \n\texpected '{2}'".format(
                  fname, result, expected_value)
        raise

print "Selftest OK"
