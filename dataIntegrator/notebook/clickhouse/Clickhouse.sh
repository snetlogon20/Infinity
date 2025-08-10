sudo systemctl restart NetworkManager

vi /etc/clickhouse-server/config.xml
<listen_host>192.168.1.100</listen_host>

systemctl stop clickhouse-server
systemctl start clickhouse-server

ps -ef | grep clickhouse-server

clickhouse-client -h 192.168.98.147

