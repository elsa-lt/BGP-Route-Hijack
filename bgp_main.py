from mininet.topo import Topo
from mininet.net import Mininet
from mininet.log import setLogLevel, info
from mininet.util import dumpNodeConnections
from mininet.cli import CLI
from mininet.node import OVSKernelSwitch

from subprocess import Popen
from time import sleep
import os
import termcolor as T
from argparse import ArgumentParser

setLogLevel('info')

parser = ArgumentParser("Configure simple BGP network in Mininet.")
parser.add_argument('--rogue', action="store_true", default=False)
parser.add_argument('--sleep', default=3, type=int)
args = parser.parse_args()

FLAGS_rogue_as = args.rogue
ROGUE_AS_NAME = 'S6'

def log(s, col="green"):
    print(T.colored(s, col))

class Router(OVSKernelSwitch):
    ID = 0
    def __init__(self, name, **kwargs):
        kwargs['inNamespace'] = True
        OVSKernelSwitch.__init__(self, name, **kwargs)
        Router.ID += 1
        self.switch_id = Router.ID

    def start(self, controllers):
        pass

    def stop(self):
        self.deleteIntfs()

    @staticmethod
    def setup():
        os.system("sysctl -w net.ipv4.ip_forward=1")  # Enable IP forwarding on the host

class Topology(Topo):  
    def __init__(self):
        super(Topology, self).__init__()
        num_hosts_per_as = 3
        num_ases = 6
        routers = []

        # Create routers
        for i in range(num_ases):
            router = self.addSwitch('S%d' % (i + 1), cls=Router)
            routers.append(router)

        # Create hosts and links within ASes
        for i in range(num_ases):
            router = 'S%d' % (i + 1)
            for j in range(num_hosts_per_as):
                hostname = 'h%d-%d' % (i + 1, j + 1)
                host = self.addHost(hostname, ip="10.%d.%d.1/24" % (i + 1, j + 1), defaultRoute="via 10.%d.%d.254" % (i + 1, j + 1))
                self.addLink(router, host)

        # Add links between ASes
        for i in range(num_ases - 1):
            self.addLink('S%d' % (i + 1), 'S%d' % (i + 2))

        # Add rogue AS
        for j in range(num_hosts_per_as):
            hostname = 'h6-%d' % (j + 1)
            host = self.addHost(hostname, ip="20.0.%d.1/24" % (j + 1), defaultRoute="via 20.0.%d.254" % (j + 1))
            self.addLink('S6', host)

        self.addLink('S1', 'S6')  # Link rogue AS to AS1

def start_router(router):
    """Function to start zebra and bgpd for BGP configurations."""
    zebra_cmd = f"/usr/lib/frr/zebra -f conf/zebra-{router.name}.conf -d -i /tmp/zebra-{router.name}.pid"
    bgpd_cmd = f"/usr/lib/frr/bgpd -f conf/bgpd-{router.name}.conf -d -i /tmp/bgp-{router.name}.pid"
    
    router.cmd(zebra_cmd)
    router.waitOutput()
    router.cmd(bgpd_cmd)
    router.waitOutput()
    router.cmd("ifconfig lo up")  # Enable loopback interface
    log(f"Started BGP and Zebra on {router.name}")

def main():
    os.system("rm -f /tmp/S*.log /tmp/S*.pid logs/*")
    os.system("mn -c >/dev/null 2>&1")
    os.system("killall -9 zebra bgpd > /dev/null 2>&1")
    os.system('pgrep -f webserver.py | xargs kill -9')

    net = Mininet(topo=Topology(), switch=Router)
    net.start()

    for router in net.switches:
        router.cmd("sysctl -w net.ipv4.ip_forward=1")  # Enable IP forwarding per router
        router.waitOutput()

    log("Waiting %d seconds for sysctl changes to take effect..." % args.sleep)
    sleep(args.sleep)

    # Start BGP and Zebra on each router
    for router in net.switches:
        if router.name == ROGUE_AS_NAME and not FLAGS_rogue_as:
            continue
       # Change path
        zebra_command = "/usr/lib/frr/zebra -f conf/zebra-%s.conf -d -i /tmp/zebra-%s.pid" % (router.name, router.name)
        bgpd_command = "/usr/lib/frr/bgpd -f conf/bgpd-%s.conf -d -i /tmp/bgp-%s.pid" % (router.name, router.name)

        router.cmd(f"{zebra_command} > logs/{router.name}-zebra-stdout 2>&1 &")
        router.waitOutput()

        # Start bgpd with output redirection
        router.cmd(f"{bgpd_command} > logs/{router.name}-bgpd-stdout 2>&1 &", shell=True)
        router.cmd("ifconfig lo up")
        router.waitOutput()
        log("Starting zebra and bgpd on %s" % router.name)

    # Configure hosts with IP and gateway
    for host in net.hosts:
        ip = "10.%d.%d.1/24" % (int(host.name.split('-')[0][1:]), int(host.name.split('-')[1]))
        gw = "10.%d.%d.254" % (int(host.name.split('-')[0][1:]), int(host.name.split('-')[1]))
        host.setIP(ip)
        host.setDefaultRoute("via " + gw)
        log(f"Configured host {host.name} with IP {ip} and gateway {gw}")

    log("Starting web servers", 'yellow')
    net.getNodeByName('h1-1').popen("python3 -m http.server 80", shell=True)
    net.getNodeByName('h6-1').popen("python3 -m http.server 80", shell=True)  # Rogue web server

    CLI(net)
    net.stop()
    os.system("killall -9 zebra bgpd")
    os.system('pgrep -f webserver.py | xargs kill -9')

if __name__ == "__main__":
    main()
