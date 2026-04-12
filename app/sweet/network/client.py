import socket
import threading
import json
import time

class Client:
    port = 1025
    receiver = None

    @classmethod
    def join_server(cls, port, receiver):
        cls.port = port.split(":")
        cls.receiver = receiver

        threading.Thread(target=cls.network_loop, daemon=True).start()

    @classmethod
    def network_loop(cls):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ip, port = cls.port
        s.connect((ip, int(port)))

        threading.Thread(target=cls.send_loop, args=(s,), daemon=True).start()

        while True:
            try:
                raw = s.recv(4096)
                if not raw:
                    break

                server_data = json.loads(raw.decode())
                cls.receiver.update_server(server_data)

            except:
                break

        s.close()
        print("Disconnected from server, reconnecting...")
        cls.join_server(cls.port[0] + ":" + cls.port[1], cls.receiver)

    @classmethod
    def send_loop(cls, sock):
        while True:
            try:
                player = cls.receiver._context["player"]
                payload = {
                    "pos": [player.x, player.y],
                    "name": player.nickname
                }

                sock.sendall(json.dumps(payload).encode())

            except:
                return

            time.sleep(0.05)
