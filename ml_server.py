import socket
import os
import random
import numpy as np
from keras.models import load_model

SERVER_ADDRESS = os.getenv("GO_ML_SOCKET", '/tmp/mysocket.sock')

if os.getenv("GO_ML_MODEL", None) is None:
    print("Provide $GO_ML_MODEL path")
    exit(1)
model_path = os.getenv("GO_ML_MODEL", None)
model = load_model(model_path)

# Remove existing socket file if it exists
if os.path.exists(SERVER_ADDRESS):
    os.remove(SERVER_ADDRESS)

# Create a new Unix domain socket
server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

# Bind the socket to the address
server_socket.bind(SERVER_ADDRESS)

# Listen for incoming connections
server_socket.listen(1)

if os.getenv("DEBUG", None) is not None:
    print(f'Server listening on {SERVER_ADDRESS}...')

# Serve incoming connections
while True:
    client_socket, client_address = server_socket.accept()
    if os.getenv("DEBUG", None) is not None:
        print(f'Accepted connection from {client_address}')

    # Receive message from client
    request = client_socket.recv(1024).decode().strip()
    if os.getenv("DEBUG", None) is not None:
        print(f'Received request: {request}')

    # Parse request ID
    request_id = request.split()[1]

    vals = np.array(list(map(float, request.split()[3:])))
    if os.getenv("DEBUG", None) is not None:
        print(request.split()[2], vals)
    vals /= 128.0
    data = [0.1] + [float(request.split()[2])] + list(vals)
    res = model.predict([data])[0][0]
    ans_number = 0
    if res > 0.5 and int(request.split()[2]) < 120:
        ans_number = 1

    # Send response to client
    response = f'{request_id}: {ans_number}'
    client_socket.sendall(response.encode())
    if os.getenv("DEBUG", None) is not None:
        print(f'Sent response: {response}')

    # Close the connection
    client_socket.close()