#!/usr/bin/env python
#
# Yapps2 is required to re-generate parser code
# http://theory.stanford.edu/~amitp/yapps/
#
# Antti Andreimann Fri Mar 22 2013

'''
A Module for parsing textual output produced by Tomcat 7 JMX Proxy Servlet
http://tomcat.apache.org/tomcat-7.0-doc/manager-howto.html#Using_the_JMX_Proxy_Servlet
Last version tested: 7.0.35
'''

from string import *
import re
from yappsrt import *

class JMXProxyOutputParserScanner(Scanner):
    patterns = [
        ('"  "', re.compile('  ')),
        ('"OK - Operation .*? returned:\\n"', re.compile('OK - Operation .*? returned:\n')),
        ('"OK - Operation .*? without return value\\n"', re.compile('OK - Operation .*? without return value\n')),
        ('"OK - Attribute .*? = "', re.compile('OK - Attribute .*? = ')),
        ("'='", re.compile('=')),
        ('", "', re.compile(', ')),
        ('"\\t"', re.compile('\t')),
        ('""', re.compile('')),
        ('": "', re.compile(': ')),
        ('"\\n"', re.compile('\n')),
        ('"Name: "', re.compile('Name: ')),
        ('"OK - .*?\\n+"', re.compile('OK - .*?\n+')),
        ('END', re.compile('$')),
        ('ARY_START', re.compile('Array\\[.+?\\] of length [0-9]+\n')),
        ('CMP_START', re.compile('javax.management.openmbean.CompositeDataSupport\\(compositeType=.+?,contents={')),
        ('CMP_END', re.compile('}\\)')),
        ('BEAN_ID', re.compile('[^\n]+')),
        ('ID', re.compile('\\w+')),
        ('CHAR', re.compile('[^\n]')),
    ]
    def __init__(self, str):
        Scanner.__init__(self,None,[],str)

class JMXProxyOutputParser(Parser):
    def search_results(self):
        self._scan('"OK - .*?\\n+"')
        rv = {}
        while self._peek('END', '"Name: "') == '"Name: "':
            bean = self.bean()
            rv.update(bean)
        END = self._scan('END')
        return rv

    def bean(self):
        self._scan('"Name: "')
        BEAN_ID = self._scan('BEAN_ID')
        self._scan('"\\n"')
        o = {}
        while self._peek('"\\n"', 'ID') == 'ID':
            property = self.property()
            o.update(property)
        self._scan('"\\n"')
        return { BEAN_ID: o }

    def property(self):
        ID = self._scan('ID')
        self._scan('": "')
        propval = self.propval()
        return { ID: propval }

    def value(self):
        _token_ = self._peek('""', 'CHAR', 'CMP_START')
        if _token_ == '""':
            self._scan('""')
            return None
        elif _token_ == 'CHAR':
            literal = self.literal()
            return literal
        else:# == 'CMP_START'
            composite = self.composite()
            return composite

    def propval(self):
        _token_ = self._peek('""', 'CHAR', 'CMP_START', 'ARY_START')
        if _token_ != 'ARY_START':
            value = self.value()
            self._scan('"\\n"')
            return value
        else:# == 'ARY_START'
            array = self.array()
            return array

    def literal(self):
        s = ""
        while 1:
            CHAR = self._scan('CHAR')
            s += CHAR
            if self._peek('CHAR', '"\\n"') != 'CHAR': break
        return convert_from_str(s)

    def array(self):
        ARY_START = self._scan('ARY_START')
        a = []
        while self._peek('"\\t"', 'END', '"\\n"', 'ID') == '"\\t"':
            self._scan('"\\t"')
            value = self.value()
            self._scan('"\\n"')
            a.append(value)
        return a

    def composite(self):
        CMP_START = self._scan('CMP_START')
        c = {}
        keyvalue = self.keyvalue()
        c.update(keyvalue)
        while self._peek('", "', 'CMP_END') == '", "':
            self._scan('", "')
            keyvalue = self.keyvalue()
            c.update(keyvalue)
        CMP_END = self._scan('CMP_END')
        return c

    def keyvalue(self):
        ID = self._scan('ID')
        self._scan("'='")
        kvvalue = self.kvvalue()
        return { ID: kvvalue }

    def kvvalue(self):
        _token_ = self._peek('""', 'CMP_START', 'CHAR')
        if _token_ == '""':
            self._scan('""')
            return None
        elif _token_ == 'CHAR':
            kvliteral = self.kvliteral()
            return kvliteral
        else:# == 'CMP_START'
            composite = self.composite()
            return composite

    def kvliteral(self):
        s = ""
        while 1:
            CHAR = self._scan('CHAR')
            s += CHAR
            if self._peek('CHAR', '", "', 'CMP_END') != 'CHAR': break
        return convert_from_str(s)

    def get_results(self):
        self._scan('"OK - Attribute .*? = "')
        propval = self.propval()
        END = self._scan('END')
        return propval

    def invoke_results(self):
        _token_ = self._peek('"OK - Operation .*? without return value\\n"', '"OK - Operation .*? returned:\\n"')
        if _token_ == '"OK - Operation .*? without return value\\n"':
            invoke_no_value = self.invoke_no_value()
        else:# == '"OK - Operation .*? returned:\\n"'
            invoke_value = self.invoke_value()
            return invoke_value

    def invoke_no_value(self):
        self._scan('"OK - Operation .*? without return value\\n"')
        END = self._scan('END')

    def invoke_value(self):
        self._scan('"OK - Operation .*? returned:\\n"')
        rv = None
        nvk_val = self.nvk_val()
        rv = nvk_val
        END = self._scan('END')
        return rv

    def nvk_val(self):
        _token_ = self._peek('""', 'CHAR', 'CMP_START', '"  "')
        if _token_ != '"  "':
            value = self.value()
            self._scan('"\\n"')
            return value
        else:# == '"  "'
            nvk_arr = self.nvk_arr()
            return nvk_arr

    def nvk_arr(self):
        rv = []
        while 1:
            self._scan('"  "')
            value = self.value()
            self._scan('"\\n"')
            rv.append(value)
            if self._peek('"  "', 'END') != '"  "': break
        return rv


def parse(rule, text):
    P = JMXProxyOutputParser(JMXProxyOutputParserScanner(text))
    return wrap_error_reporter(P, rule)




def convert_from_str(s):
    try:
        return to_boolean(s)
    except ValueError:
        pass

    try:
        return int(s)
    except ValueError:
        pass

    try:
        return float(s)
    except ValueError:
        pass

    return s

def to_boolean(s):
    if s.lower() == 'true':
        return True
    if s.lower() == 'false':
        return False

    raise ValueError('Not a boolean: %s' % s)
