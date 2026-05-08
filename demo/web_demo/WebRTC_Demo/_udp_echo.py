import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("0.0.0.0", 19999))
s.settimeout(15)
print("[*] UDP echo server on 0.0.0.0:19999", flush=True)
try:
    data, addr = s.recvfrom(1024)
    print(f"[+] recv from {addr}: {data}", flush=True)
    s.sendto(b"ECHO:" + data, addr)
    print(f"[+] replied", flush=True)
except socket.timeout:
    print("[-] timeout", flush=True)
