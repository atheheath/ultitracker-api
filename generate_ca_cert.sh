apt-get update
apt-get install -y software-properties-common
add-apt-repository universe
add-apt-repository ppa:certbot/certbot
apt-get update
apt-get install -y certbot 
certbot certonly --standalone --agree-tos --email admin@ultitracker.com -d api.ultitracker.com -n
