import subprocess
import bluetooth

# Define the name of the service
SERVICE_NAME = "SSH over Bluetooth"

# Define a unique identifier for the service
SERVICE_ID = "c5c91a1e-162f-11ec-9621-0242ac130002"

# Set up Bluetooth socket
server_socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
server_socket.bind(("", bluetooth.PORT_ANY))
server_socket.listen(1)

# Advertise the service
bluetooth.advertise_service(server_socket, SERVICE_NAME, service_id=SERVICE_ID)

print("Waiting for connection...")

# Accept incoming connection
client_socket, client_info = server_socket.accept()
print("Accepted connection from", client_info)

try:
    # Run SSH server subprocess
    ssh_process = subprocess.Popen(["/usr/sbin/sshd", "-i", "-f", "/etc/ssh/sshd_config_bluetooth"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    print("SSH server started")

    # Wait for the connection to close
    client_socket.recv(1024)

finally:
    # Clean up
    print("Closing connection")
    client_socket.close()
    server_socket.close()
    ssh_process.terminate()
