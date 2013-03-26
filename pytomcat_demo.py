#!/usr/bin/env python

import re
from tomcat import Tomcat

def main():
    t = Tomcat('localhost', 'admin', 'admin')

    print 'Number of Threads: {0}'.format(len(t.dump_all_threads()))
    print 'Cluster: {0}'.format(t.is_clustered())
    print 'Cluster Name: {0}'.format(t.cluster_name())
    print 'Cluster Members: {0}'.format(map(lambda x: x['hostname'], t.cluster_members().values()))
    print 'Active Members: {0}'.format(map(lambda x: x['hostname'], t.active_members().values()))
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
    for k, v in t.sessions_summary().iteritems():
        print '\t - {0:<50}: {1}'.format(re.sub('^.*?,','',k), v['activeSessions'])

    print "Active Session IDs:"
    for k, v in t.list_sessions().iteritems():
        if len(v) > 0:
            print '\t - {0}'.format(re.sub('^.*?,','',k))
            for id in v:
                print '\t\t - {0}'.format(id)

    #t.undeploy_old_versions('localhost')
    t.undeploy_old_versions()
    t.run_gc()

if __name__ == "__main__":
    main()
