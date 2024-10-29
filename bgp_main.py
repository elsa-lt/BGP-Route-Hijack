#!/usr/bin/env python

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.log import lg, info, setLogLevel
from mininet.util import dumpNodeConnections, quietRun, moveIntf
from mininet.cli import CLI
from mininet.node import Switch, OVSKernelSwitch

from subprocess import Popen, PIPE, check_output
from time import sleep, time
from multiprocessing import Process
from argparse import ArgumentParser

import sys
import os
import termcolor as T
import time

setLogLevel('info')

parser = ArgumentParser("Configure BGP network in Mininet.")
parser.add_argument('--rogue', action="store_true", default=False)
parser.add_argument('--sleep', default=3, type=int)
args = parser.parse_args()

FLAGS_rogue_as = args.rogue
ROGUE_AS_NAME = 'R6'

def log(s, col="green"):
    print(T.colored(s, col))


class Router(Switch):
    """Defines a new router that is inside a network namespace so that the
    individual routing entries don't collide.

    """
    ID = 0
    def __init__(self, name, **kwargs):
        kwargs['inNamespace'] = True
        Switch.__init__(self, name, **kwargs)
        Router.ID += 1
        self.switch_id = Router.ID

    @staticmethod
    def setup():
        return

    def start(self, controllers):
        pass

    def stop(self):
        self.deleteIntfs()

    def log(self, s, col="magenta"):
        print(T.colored(s, col))


class GraphTopo(Topo):
    """The Autonomous System topology is graph topology
            AS4
           / | \
          /  |  \
         AS2-----AS5
         |\  |   /|
         | \ |  / |
         |  AS3   |
         |  /     |
         | /      |
         AS1     AS6

    """
    def __init__(self):
        # Add default members to class.
        super(GraphTopo, self ).__init__()
        num_hosts_per_as = 3
        num_ases = 6
        num_hosts = num_hosts_per_as * num_ases
        # The topology has one router per AS
        # set 1-6 routers
        routers = []
        for i in xrange(num_ases):
            router = self.addSwitch('S%d' % (i+1))
            
        routers.append(router)
        # set R1-R6 add 3 host each
        hosts = []
        for i in range(num_ases):
            router = self.addSwitch('S%d' % (i+1))

        for i in range(num_ases):
            router = 'S%d' % (i+1)
            for j in range(num_hosts_per_as):
                hostname = 'h%d-%d' % (i+1, j+1)

        # add link for ASes
        self.addLink('S2', 'S3')
        self.addLink('S2', 'S4')
        self.addLink('S2', 'S5')

        self.addLink('S3', 'S4')
        self.addLink('S3', 'S5')

        self.addLink('S4', 'S5')

        self.addLink('S1', 'S2')
        self.addLink('S1', 'S3')

        self.addLink('S5', 'S6')

        self.addLink('S1', 'S4')
        return


def getIP(hostname):
    AS, idx = hostname.replace('h', '').split('-')
    AS = int(AS)
    if AS == 6:
        AS = 1
    ip = '%s.0.%s.1/24' % (10+AS, idx)
    return ip


def getGateway(hostname):
    AS, idx = hostname.replace('h', '').split('-')
    AS = int(AS)
    # This condition gives AS4 the same IP range as AS3 so it can be an
    # attacker.
    if AS == 6:
        AS = 1
    gw = '%s.0.%s.254' % (10+AS, idx)
    return gw


def startWebserver(net, hostname, text="Default web server"):
    host = net.getNodeByName(hostname)
    return host.popen("python webserver.py --text '%s'" % text, shell=True)


def main():
    os.system("rm -f /tmp/R*.log /tmp/R*.pid logs/*")
    os.system("mn -c >/dev/null 2>&1")
    os.system("killall -9 zebra bgpd > /dev/null 2>&1")
    os.system('pgrep -f webserver.py | xargs kill -9')

    net = Mininet(topo=GraphTopo(), switch=Router)
    net.start()
    for router in net.switches:
        router.cmd("sysctl -w net.ipv4.ip_forward=1")
        router.waitOutput()

    log("Waiting %d seconds for sysctl changes to take effect..." % args.sleep)
    sleep(args.sleep)

    for router in net.switches:
        if router.name == ROGUE_AS_NAME and not FLAGS_rogue_as:
            continue
        
        # Updated zebra and bgpd commands with new paths
        zebra_command = "/usr/lib/frr/zebra -f conf/zebra-%s.conf -d -i /tmp/zebra-%s.pid" % (router.name, router.name)
        bgpd_command = "/usr/lib/frr/bgpd -f conf/bgpd-%s.conf -d -i /tmp/bgp-%s.pid" % (router.name, router.name)

        # Start zebra with output redirection
        router.cmd(f"{zebra_command} > logs/{router.name}-zebra-stdout 2>&1 &")
        router.waitOutput()

        # Start bgpd with output redirection
        router.cmd(f"{bgpd_command} > logs/{router.name}-bgpd-stdout 2>&1 &", shell=True)
        router.cmd("ifconfig lo up")
        router.waitOutput()
        log("Starting zebra and bgpd on %s" % router.name)

    for host in net.hosts:
        host.cmd("ifconfig %s-eth0 %s" % (host.name, getIP(host.name)))
        host.cmd("route add default gw %s" % (getGateway(host.name)))

    log("Starting web servers", 'yellow')
    startWebserver(net, 'h1-1', "Default web server")
    startWebserver(net, 'h6-1', "*** Attacker web server ***")

    CLI(net)
    net.stop()
    os.system("killall -9 zebra bgpd")
    os.system('pgrep -f webserver.py | xargs kill -9')


if __name__ == "__main__":
    main()
