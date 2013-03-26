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
%%
parser JMXProxyOutputParser:
    token END: "$"

    token ARY_START: "Array\\[.+?\\] of length [0-9]+\n"
    token CMP_START: "javax.management.openmbean.CompositeDataSupport\\(compositeType=.+?,contents={"
    token CMP_END: "}\\)"

    token BEAN_ID: "[^\n]+"
    token ID: "\\w+"
    token CHAR: "[^\n]"

    rule search_results: "OK - .*?\n+"  {{ rv = {} }}
                         ( bean         {{ rv.update(bean) }}
                         )* END         {{ return rv }}

    rule bean: "Name: " BEAN_ID "\n"    {{ o = {} }}
               ( property               {{ o.update(property) }}
               )* "\n"                  {{ return { BEAN_ID: o } }} 

    rule property: ID ": " propval      {{ return { ID: propval } }}

    rule value:   ""                    {{ return None }}
                | literal               {{ return literal }}
                | composite             {{ return composite }}

    rule propval:   value "\n"          {{ return value }}
                  | array               {{ return array }}

    rule literal:                       {{ s = "" }}
                  ( CHAR                {{ s += CHAR }}
                  )+                    {{ return convert_from_str(s) }}

    rule array: ARY_START               {{ a = [] }}
                ( "\t" value "\n"       {{ a.append(value) }}
                )*                      {{ return a }}

    rule composite: CMP_START           {{ c = {} }}
                    keyvalue            {{ c.update(keyvalue) }}
                    ( ", " keyvalue     {{ c.update(keyvalue) }}
                    )* CMP_END          {{ return c }}

    rule keyvalue: ID '=' kvvalue       {{ return { ID: kvvalue } }}

    # We need to duplicate value and literal parsing rules to work
    # around limitations in Yapps2 generated lookahead code

    rule kvvalue:   ""                  {{ return None }}
                  | kvliteral           {{ return kvliteral }}
                  | composite           {{ return composite }}

    rule kvliteral:                     {{ s = "" }}
                    ( CHAR              {{ s += CHAR }}
                    )+                  {{ return convert_from_str(s) }}

    rule get_results: "OK - Attribute .*? = "
                      propval END       {{ return propval }}

    rule invoke_results:   invoke_no_value
                         | invoke_value {{ return invoke_value }}

    rule invoke_no_value: "OK - Operation .*? without return value\n"
                          END

    rule invoke_value: "OK - Operation .*? returned:\n"
                                        {{ rv = None }}
                       nvk_val          {{ rv = nvk_val }}
                       END              {{ return rv }}

    rule nvk_val:   value "\n"          {{ return value }}
                  | nvk_arr             {{ return nvk_arr }}

    rule nvk_arr:                       {{ rv = [] }}
                 ( "  " value "\n"      {{ rv.append(value) }}
                 )+                     {{ return rv }}

%%

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
