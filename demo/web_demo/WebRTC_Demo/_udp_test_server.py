#!/usr/bin/env python3
import socket
import time

HOST = "0.0.0.0"
PORT = 19999

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, PORT))
sock.settimeout(10)

print(f"[*] UDP echo server listening on {HOST}:{PORT}")
print(f"[*] Send a UDP packet to 127.0.0.1:{PORT} from Windows to test")

try:
    while True:
        data, addr = sock.recvfrom(1024)
        print(f"[+] Received from {addr}: {data.decode('utf-8', errors='ignore').strip()}")
        sock.sendto(b"ECHO: " + data, addr)
        print(f"[+] Replied to {addr}")
except socket.timeout:
    print("[-] Timeout, no packet received")
except KeyboardInterrupt:
    pass
finally:
    sock.close()
