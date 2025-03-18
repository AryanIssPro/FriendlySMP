#start the tailscale service
sudo tailscaled & 
sudo tailscale up

./sync.sh

playit
cd crafty
python3 -m venv .venv
source .venv/bin/activate
python3 main.py