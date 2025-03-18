sudo apt update
sudo apt install openjdk-21-jdk -y

curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscaled & 
sudo tailscale up

chmod +x start.sh
chmod +x sync.sh
chmod +x backup.sh