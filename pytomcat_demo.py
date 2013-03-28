#!/usr/bin/env python

import re
from tomcat import Tomcat,TomcatCluster

def main():
    t = Tomcat('localhost', 'admin', 'admin')

    print 'Number of Threads: {0}'.format(len(t.dump_all_threads()))
    has_cluster = t.has_cluster()
    print 'Cluster: {0}'.format(has_cluster)
    if has_cluster:
        print '\tName: {0}'.format(t.cluster_name())
        print '\tMembers: {0}'.format(map(lambda x: x['hostname'], t.cluster_members().values()))
        print '\tActive: {0}'.format(map(lambda x: x['hostname'], t.active_members().values()))

    print 'Memory:'
    print '\tMax Heap Size     : {0:3} MiB'.format(t.max_heap() / 1048576)
    print '\tMax Non-Heap Size : {0:3} MiB'.format(t.max_nonheap() / 1048576)
    print '\tPools:'
    for k, v in sorted(t.memory_usage().iteritems()):
        print '\t\t{0:<30}: {1:3}%'.format(k, v)
    print 'VHosts:'
    for v in t.vhosts().values():
        print '\t- {name}'.format(**v)
    print 'Connectors:'
    for v in t.find_connectors(): 
        print '\t- {0}'.format(v)

    print "Webapps:"
    for k, a in t.list_webapps().iteritems():
        print '\t - {baseName:<20} {path:<20} {stateName:<10} {webappVersion}'.format(**a)

    print "Session counts:"
    for k, v in t.find_managers().iteritems():
        print '\t - {0:<30}: {1}'.format(k, v['activeSessions'])

    print "Active Session IDs:"
    for k, v in t.list_sessions().iteritems():
        if len(v) > 0:
            print '\t - {0}'.format(re.sub('^.*?,','',k))
            for id in v:
                print '\t\t - {0}'.format(id)

    t.undeploy_old_versions()
    t.expire_sessions('/manager')
    t.run_gc()
    c = TomcatCluster('localhost', 'admin', 'admin')
    print 'Cluster wide Max Heap: %s' % c.run_command('max_heap')

if __name__ == "__main__":
    main()
