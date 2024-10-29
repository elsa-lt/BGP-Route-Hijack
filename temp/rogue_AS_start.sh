#!/bin/bash

echo "Killing any existing rogue AS"
./rogue_AS_stop.sh

echo "Starting rogue AS"
sudo python3 run.py --node S4 --cmd "/home/mininet/usr/lib/frr/zebra -f conf/zebra-S4.conf -d -i /tmp/zebra-S4.pid > logs/S4-zebra-stdout"
sudo python3 run.py --node S4 --cmd "/home/mininet/usr/lib/frr/bgpd -f conf/bgpd-S4.conf -d -i /tmp/bgpd-S4.pid > logs/S4-bgpd-stdout"