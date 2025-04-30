import socket

def start_udp_server():
    host = "0.0.0.0"  # Listen on all available interfaces
    port = 10514        # Port to listen on

    # Create a UDP socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        server_socket.bind((host, port))
        print(f"UDP server listening on port {port}...")

        while True:
            # Receive data from client
            data, addr = server_socket.recvfrom(1024)  # Buffer size is 1024 bytes
            print(f"Received message from {addr}: {data.decode('utf-8')}")

if __name__ == "__main__":
    start_udp_server()