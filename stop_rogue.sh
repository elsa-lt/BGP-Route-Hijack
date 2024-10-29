#!/bin/bash

sudo python3 run.py --node S6 --cmd "pgrep -f zebra-S4 | sudo xargs kill -9"
sudo python3 run.py --node S6 --cmd "pgrep -f bgpd-S4 | sudo xargs kill -9"
