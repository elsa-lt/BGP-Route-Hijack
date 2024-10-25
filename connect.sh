router=${1:-S1}
echo "Connecting to $router shell"

sudo python3 run.py --node $router --cmd "telnet localhost bgpd"
