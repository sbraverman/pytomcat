#!/usr/bin/env python

from parser import parse

# Testing code below
def test():
    input='''OK - Number of results: 3

Name: java.lang:type=Memory
modelerType: sun.management.MemoryImpl
Verbose: false
ObjectPendingFinalizationCount: 0

Name: java.lang:type=MemoryPool,name=Par Survivor Space
MemoryManagerNames: Array[java.lang.String] of length 2
	ConcurrentMarkSweep
	ParNew
MemoryPoolNames: Array[java.lang.String] of length 1
	Code Cache

Name: java.lang:type=MemoryPool,name=CMS Old Gen
Name: CMS Old Gen
Usage: javax.management.openmbean.CompositeDataSupport(compositeType=javax.management.openmbean.CompositeType(name=java.lang.management.MemoryUsage,items=((itemName=committed,itemType=javax.management.openmbean.SimpleType(name=java.lang.Long)),(itemName=init,itemType=javax.management.openmbean.SimpleType(name=java.lang.Long)),(itemName=max,itemType=javax.management.openmbean.SimpleType(name=java.lang.Long)),(itemName=used,itemType=javax.management.openmbean.SimpleType(name=java.lang.Long)))),contents={committed=65404928, init=65404928, max=110362624, used=11296184})
MemoryManagerNames: Array[java.lang.String] of length 1
	ConcurrentMarkSweep
UsageThreshold: 0.3
waitedTime: -1
hostname: 10.0.0.6
webappVersion: 
deploymentDescriptor: <!-- Blah, blah, ({ blah }), this   can not crash -->

'''
    expected_output = {'java.lang:type=MemoryPool,name=CMS Old Gen': {'Usage': {'max': 110362624, 'init': 65404928, 'used': 11296184, 'committed': 65404928}, 'MemoryManagerNames': ['ConcurrentMarkSweep'], 'UsageThreshold': 0.3, 'waitedTime': -1, 'hostname': '10.0.0.6', 'webappVersion': None, 'deploymentDescriptor': '<!-- Blah, blah, ({ blah }), this   can not crash -->', 'Name': 'CMS Old Gen'}, 'java.lang:type=Memory': {'modelerType': 'sun.management.MemoryImpl', 'Verbose': False, 'ObjectPendingFinalizationCount': 0}, 'java.lang:type=MemoryPool,name=Par Survivor Space': {'MemoryManagerNames': ['ConcurrentMarkSweep', 'ParNew'], 'MemoryPoolNames': ['Code Cache']}}

    assert parse('search_results', input) == expected_output

    input = "OK - Attribute get 'java.lang:type=Memory' - HeapMemoryUsage = javax.management.openmbean.CompositeDataSupport(compositeType=javax.management.openmbean.CompositeType(name=java.lang.management.MemoryUsage,items=((itemName=committed,itemType=javax.management.openmbean.SimpleType(name=java.lang.Long)),(itemName=init,itemType=javax.management.openmbean.SimpleType(name=java.lang.Long)),(itemName=max,itemType=javax.management.openmbean.SimpleType(name=java.lang.Long)),(itemName=used,itemType=javax.management.openmbean.SimpleType(name=java.lang.Long)))),contents={committed=85000192, init=0, max=129957888, used=16825392})\n"
    expected_output = {'max': 129957888, 'init': 0, 'used': 16825392, 'committed': 85000192}
    assert parse('get_results', input) == expected_output

    input = "OK - Attribute get 'java.lang:type=Memory' - HeapMemoryUsage - key 'max' = 129957888\n"
    expected_output = 129957888
    assert parse('get_results', input) == expected_output

    input = "OK - Attribute get 'java.lang:type=Runtime' - InputArguments = [Ljava.lang.String;@213dda1\n"
    expected_output = '[Ljava.lang.String;@213dda1'
    assert parse('get_results', input) == expected_output

    input = "OK - Operation gc without return value\n"
    expected_output = None
    assert parse('invoke_results', input) == expected_output

    input = '''OK - Operation findConnectors returned:
  Connector[HTTP/1.1-8080]
  Connector[AJP/1.3-8009]
'''
    expected_output = ['Connector[HTTP/1.1-8080]', 'Connector[AJP/1.3-8009]']
    assert parse('invoke_results', input) == expected_output

    input = '''OK - Operation listSessionIds returned:
7238598882F2AA7CA057015AB1C62D50 

'''
    expected_output = '7238598882F2AA7CA057015AB1C62D50 '
    assert parse('invoke_results', input) == expected_output

    input = '''OK - Operation dumpAllThreads returned:
  javax.management.openmbean.CompositeDataSupport(compositeType=javax.management.openmbean.CompositeType(name=java.lang.management.ThreadInfo,items=((itemName=blockedCount,itemType=javax.management.openmbean.SimpleType(name=java.lang.Long)),(itemName=blockedTime,itemType=javax.management.openmbean.SimpleType(name=java.lang.Long)),(itemName=inNative,itemType=javax.management.openmbean.SimpleType(name=java.lang.Boolean)),(itemName=lockInfo,itemType=javax.management.openmbean.CompositeType(name=java.lang.management.LockInfo,items=((itemName=className,itemType=javax.management.openmbean.SimpleType(name=java.lang.String)),(itemName=identityHashCode,itemType=javax.management.openmbean.SimpleType(name=java.lang.Integer))))),(itemName=lockName,itemType=javax.management.openmbean.SimpleType(name=java.lang.String)),(itemName=lockOwnerId,itemType=javax.management.openmbean.SimpleType(name=java.lang.Long)),(itemName=lockOwnerName,itemType=javax.management.openmbean.SimpleType(name=java.lang.String)),(itemName=lockedMonitors,itemType=javax.management.openmbean.ArrayType(name=[Ljavax.management.openmbean.CompositeData;,dimension=1,elementType=javax.management.openmbean.CompositeType(name=java.lang.management.MonitorInfo,items=((itemName=className,itemType=javax.management.openmbean.SimpleType(name=java.lang.String)),(itemName=identityHashCode,itemType=javax.management.openmbean.SimpleType(name=java.lang.Integer)),(itemName=lockedStackDepth,itemType=javax.management.openmbean.SimpleType(name=java.lang.Integer)),(itemName=lockedStackFrame,itemType=javax.management.openmbean.CompositeType(name=java.lang.StackTraceElement,items=((itemName=className,itemType=javax.management.openmbean.SimpleType(name=java.lang.String)),(itemName=fileName,itemType=javax.management.openmbean.SimpleType(name=java.lang.String)),(itemName=lineNumber,itemType=javax.management.openmbean.SimpleType(name=java.lang.Integer)),(itemName=methodName,itemType=javax.management.openmbean.SimpleType(name=java.lang.String)),(itemName=nativeMethod,itemType=javax.management.openmbean.SimpleType(name=java.lang.Boolean))))))),primitiveArray=false)),(itemName=lockedSynchronizers,itemType=javax.management.openmbean.ArrayType(name=[Ljavax.management.openmbean.CompositeData;,dimension=1,elementType=javax.management.openmbean.CompositeType(name=java.lang.management.LockInfo,items=((itemName=className,itemType=javax.management.openmbean.SimpleType(name=java.lang.String)),(itemName=identityHashCode,itemType=javax.management.openmbean.SimpleType(name=java.lang.Integer)))),primitiveArray=false)),(itemName=stackTrace,itemType=javax.management.openmbean.ArrayType(name=[Ljavax.management.openmbean.CompositeData;,dimension=1,elementType=javax.management.openmbean.CompositeType(name=java.lang.StackTraceElement,items=((itemName=className,itemType=javax.management.openmbean.SimpleType(name=java.lang.String)),(itemName=fileName,itemType=javax.management.openmbean.SimpleType(name=java.lang.String)),(itemName=lineNumber,itemType=javax.management.openmbean.SimpleType(name=java.lang.Integer)),(itemName=methodName,itemType=javax.management.openmbean.SimpleType(name=java.lang.String)),(itemName=nativeMethod,itemType=javax.management.openmbean.SimpleType(name=java.lang.Boolean)))),primitiveArray=false)),(itemName=suspended,itemType=javax.management.openmbean.SimpleType(name=java.lang.Boolean)),(itemName=threadId,itemType=javax.management.openmbean.SimpleType(name=java.lang.Long)),(itemName=threadName,itemType=javax.management.openmbean.SimpleType(name=java.lang.String)),(itemName=threadState,itemType=javax.management.openmbean.SimpleType(name=java.lang.String)),(itemName=waitedCount,itemType=javax.management.openmbean.SimpleType(name=java.lang.Long)),(itemName=waitedTime,itemType=javax.management.openmbean.SimpleType(name=java.lang.Long)))),contents={blockedCount=0, blockedTime=-1, inNative=false, lockInfo=javax.management.openmbean.CompositeDataSupport(compositeType=javax.management.openmbean.CompositeType(name=java.lang.management.LockInfo,items=((itemName=className,itemType=javax.management.openmbean.SimpleType(name=java.lang.String)),(itemName=identityHashCode,itemType=javax.management.openmbean.SimpleType(name=java.lang.Integer)))),contents={className=com.sun.jmx.remote.internal.ArrayNotificationBuffer, identityHashCode=220888094}), lockName=com.sun.jmx.remote.internal.ArrayNotificationBuffer@d2a7c1e, lockOwnerId=-1, lockOwnerName=null, lockedMonitors=[Ljavax.management.openmbean.CompositeData;@43684726, lockedSynchronizers=[Ljavax.management.openmbean.CompositeData;@7317325c, stackTrace=[Ljavax.management.openmbean.CompositeData;@77eb710b, suspended=false, threadId=100, threadName=RMI TCP Connection(39)-192.168.56.1, threadState=TIMED_WAITING, waitedCount=1032, waitedTime=-1})
'''
    expected_output = [{'blockedTime': -1, 'blockedCount': 0, 'lockedSynchronizers': '[Ljavax.management.openmbean.CompositeData;@7317325c', 'lockName': 'com.sun.jmx.remote.internal.ArrayNotificationBuffer@d2a7c1e', 'lockedMonitors': '[Ljavax.management.openmbean.CompositeData;@43684726', 'waitedCount': 1032, 'stackTrace': '[Ljavax.management.openmbean.CompositeData;@77eb710b', 'waitedTime': -1, 'threadState': 'TIMED_WAITING', 'threadName': 'RMI TCP Connection(39)-192.168.56.1', 'lockOwnerName': 'null', 'lockOwnerId': -1, 'suspended': False, 'threadId': 100, 'lockInfo': {'className': 'com.sun.jmx.remote.internal.ArrayNotificationBuffer', 'identityHashCode': 220888094}, 'inNative': False}]
    assert parse('invoke_results', input) == expected_output

    print "Selftest PASSED"

if __name__ == '__main__':
    from sys import argv, stdin
    if len(argv) >= 1:
        if len(argv) >= 2:
            f = open(argv[1],'r')
            print parse('search_results', f.read())
        else:
            test()
