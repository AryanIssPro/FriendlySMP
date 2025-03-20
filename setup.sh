echo 'export TZ=Asia/Kolkata' >> ~/.bashrc
source ~/.bashrc

sudo apt update
sudo apt install openjdk-21-jdk -y

curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscaled & 
sudo tailscale up

curl -SsL https://playit-cloud.github.io/ppa/key.gpg | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/playit.gpg >/dev/null
echo "deb [signed-by=/etc/apt/trusted.gpg.d/playit.gpg] https://playit-cloud.github.io/ppa/data ./" | sudo tee /etc/apt/sources.list.d/playit-cloud.list
sudo apt update
sudo apt install playit -y

chmod +x start.sh
chmod +x sync.sh
