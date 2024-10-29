#!/usr/bin/env python3

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

parser = ArgumentParser("Configure simple BGP network in Mininet.")
parser.add_argument('--rogue', action="store_true", default=False)
parser.add_argument('--sleep', default=3, type=int)
args = parser.parse_args()

FLAGS_rogue_as = args.rogue
ROGUE_AS_NAME = 'S6'


def log(s, col="green"):
    print(T.colored(s, col))


class Router(Switch):
    """Defines a router in a network namespace with separate routing entries."""

    ID = 0

    def __init__(self, name, **kwargs):
        kwargs['inNamespace'] = True
        super(Router, self).__init__(name, **kwargs)
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
    """Graph topology for Autonomous Systems setup with routers and hosts."""

    def __init__(self):
        super(GraphTopo, self).__init__()
        num_hosts_per_as = 3
        num_ases = 6

        # Set up routers and hosts
        routers = []
        for i in range(num_ases):
            router = self.addSwitch(f'R{i+1}')
            routers.append(router)

        for i in range(num_ases):
            router = f'R{i+1}'
            for j in range(num_hosts_per_as):
                hostname = f'h{i+1}-{j+1}'
                host = self.addHost(hostname)
                self.addLink(router, host)

        # Interconnect the AS routers
        self.addLink('S2', 'S3')
        self.addLink('S2', 'S4')
        self.addLink('S2', 'S5')
        self.addLink('S3', 'S4')
        self.addLink('S3', 'S5')
        self.addLink('S4', 'S5')
        self.addLink('S1', 'S2')
        self.addLink('S1', 'S3')
        self.addLink('S5', 'S6')


def getIP(hostname):
    AS, idx = hostname.replace('h', '').split('-')
    AS = int(AS)
    if AS == 6:
        AS = 1
    ip = f'10.{10+AS}.0.{idx}/24'
    return ip


def getGateway(hostname):
    AS, idx = hostname.replace('h', '').split('-')
    AS = int(AS)
    if AS == 6:
        AS = 1
    gw = f'10.{10+AS}.0.254'
    return gw


def start_router(router):
    """Function to start zebra and bgpd for BGP configurations."""
    zebra_cmd = f"/usr/lib/frr/zebra -f conf/zebra-{router.name}.conf -d -i /tmp/zebra-{router.name}.pid"
    bgpd_cmd = f"/usr/lib/frr/bgpd -f conf/bgpd-{router.name}.conf -d -i /tmp/bgp-{router.name}.pid"

    router.cmd(zebra_cmd)
    router.waitOutput()
    router.cmd(bgpd_cmd)
    router.waitOutput()
    router.cmd("ifconfig lo up")
    log(f"Started BGP and Zebra on {router.name}")


def startWebserver(net, hostname, text="Default web server"):
    host = net.getNodeByName(hostname)
    return host.popen(f"python3 -m http.server 80 --bind 0.0.0.0 & echo '{text}'", shell=True)


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

    log(f"Waiting {args.sleep} seconds for sysctl changes to take effect...")
    sleep(args.sleep)

    for router in net.switches:
        if router.name == ROGUE_AS_NAME and not FLAGS_rogue_as:
            continue
        start_router(router)

    for host in net.hosts:
        ip = getIP(host.name)
        gw = getGateway(host.name)
        host.cmd(f"ifconfig {host.name}-eth0 {ip}")
        host.cmd(f"route add default gw {gw}")

    log("Starting web servers", 'yellow')
    startWebserver(net, 'h1-1', "Default web server")
    startWebserver(net, 'h6-1', "*** Attacker web server ***")

    CLI(net)
    net.stop()
    os.system("killall -9 zebra bgpd")
    os.system('pgrep -f webserver.py | xargs kill -9')


if __name__ == "__main__":
    main()
