from network import WLAN, STA_IF, AP_IF
from socket import socket
from time import sleep
from os import listdir
from machine import reset
from ure import search

FILE_NAME = 'credentials'
PATTERN = r'"ssid"\s*:\s*"([^"]*)".*?"password"\s*:\s*"([^"]*)"'


class WiFiManager:
    """ Manages WiFi connection.

    Either connects to WiFi with saved credentials on file or starts an access point to provide them
    """

    def __init__(self, ssid='WiFiManager', password='wifimanager', timeout=10):
        """
        Args:
            ssid (str, optional): Access point network name. Defaults to 'WiFiManager'.
            password (str, optional): Access point network password. Defaults to 'wifimanager'.
            timeout (int, optional): Seconds to wait before giving up on connecting on saved network. Defaults to 10.
        """
        self.ssid = ssid
        self.password = password
        self.timeout = timeout
        self.client = WLAN(STA_IF)
        self.client.active(True)
        self._start()

    def _start(self):
        if FILE_NAME in listdir():
            self._start_client()
            if (self.client.isconnected()):
                print('Successfully connected to WiFi')
                return
        print("Could not connect to WiFi")
        self._start_access_point()

    def _list_networks(self):
        return [
            {
                'ssid': ssid.decode('uft-8'),
                'security': 'true' if security != 0 else 'false',
                'hidden': 'false' if hidden == 1 else 'true',
            } for (ssid, bssid, channel, RSSI, security, hidden) in
            sorted(self.client.scan(), key=lambda i: i[3], reverse=True)
            if ssid
        ]

    def _write_credentials(self, ssid: str, password: str):
        with open(FILE_NAME, 'w+') as f:
            f.write(f'{ssid}\n{password}')
            f.close()

    def _read_credentials(self):
        with open(FILE_NAME, "r") as f:
            lines = f.read().splitlines()
            creds = lines[:2] + ['']*(2 - len(lines))
            f.close()
        return creds

    def _start_client(self):
        ssid, password = self._read_credentials()
        self.client.connect(ssid, password)
        print(f'Trying to connect to network {ssid}, {password}')
        t = 0
        while not self.client.isconnected():
            if (t >= self.timeout):
                break
            print(".", end="")
            t += 1
            sleep(1)

    def _start_access_point(self):
        print("Starting access point")
        access_point = WLAN(AP_IF)
        access_point.config(essid=self.ssid, password=self.password)
        access_point.active(True)
        while not access_point.active():
            pass
        ip = access_point.ifconfig()[0]
        print(f'ssid: {self.ssid}\npassword: {self.password}\nip: {ip}')
        connection = self._open_socket(ip)
        self._serve(connection)

    def _open_socket(self, ip) -> socket:
        address = (ip, 80)
        connection = socket()
        connection.bind(address)
        connection.listen(1)
        return connection

    def _serve(self, connection: socket):
        while True:
            client = connection.accept()[0]
            request = client.recv(1024)
            creds = self._handle_request(request)
            if creds:
                print("Received credentials. \nRebooting...")
                self._write_credentials(creds[0], creds[1])
                reset()
            networks = self._list_networks()
            client.send(self._webpage(networks))
            client.close()

    def _handle_request(self, request: bytes):
        lines = request.splitlines()
        method = lines[0].decode("uft-8")
        body = lines[-1].decode("uft-8")
        if "POST" not in method:
            return
        match = search(PATTERN, body)
        if (match == None):
            return
        return match.groups()

    def _webpage(self, data) -> str:
        return f"""
<!DOCTYPE html>
<html>
<body>
    <div>
        <div id="network-list" class="network-list">
            <p>Networks</p>
        </div>
        <div id="modal" class="modal">
            <p>Connecting to: </p>
            <p id="ssid"></p>
            <input id="password" type="password" placeholder="password">
            <div class="buttons">
                <button onclick="closeModal()">CLOSE</button>
                <button onclick="connect()">CONNECT</button>
            </div>
        </div>
    </div>
</body>
<script>
    const networkList = document.getElementById("network-list")
    const modal = document.getElementById("modal")
    const ssid = document.getElementById("ssid")
    const password = document.getElementById("password")
    const openModal = (ssidName) => {{
        ssid.textContent = ssidName
        modal.style.display = "flex"
        networkList.style.pointerEvents = "none"
    }}
    const data ={data}
    data.forEach(d => {{
        const button = document.createElement("button");
        button.textContent = d.ssid
        button.onclick = () => openModal(d.ssid)
        networkList.appendChild(button)
    }})
    const connect = () => {{
        fetch("http://192.168.4.1", {{
            method: "POST",
            body: JSON.stringify({{
                ssid: ssid.textContent,
                password: password.value
            }})
        }})
        modal.innerHTML = "<p>Device rebooted</p><p>You can close this</p></div>"
    }}
    const closeModal = () => {{
        modal.style.display = "none"
        networkList.style.pointerEvents = "all"
    }}
</script>
<style>
    input {{
        width: 90%;
        padding: 10px;
        margin-bottom: 10px;
        border: 1px solid grey;
        border-radius: 4px;
    }}
    div {{
        font-family: Arial, sans-serif;
    }}
    .network-list {{
        display: flex;
        align-items: center;
        justify-content: center;
        flex-direction: column;
    }}
    button {{
        background-color: #2596be;
        color: white;
        border: none;
        padding: 2vh;
        margin: 1vh;
        border-radius: 4px;
        width: 60%;
    }}
    button:hover {{
        background-color: #1d7ea1;
    }}
    .buttons {{
        display: flex;
        padding: 0 5vw;
    }}
    .modal {{
        display: none;
        position: fixed;
        z-index: 10;
        border: 1px solid gray;
        border-radius: 10px;
        background-color: white;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        align-items: center;
        justify-content: center;
        flex-direction: column;
        padding: 10px;
        left: 50%;
        top: 50%;
        transform: translateX(-50%) translateY(-50%);
    }}
</style>
</html>
        """
