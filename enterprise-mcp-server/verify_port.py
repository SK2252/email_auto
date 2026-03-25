import socket
s = socket.socket()
result = s.connect_ex(('localhost', 9000))
s.close()
print('Port 9000 OPEN' if result == 0 else f'Port 9000 not open — code {result}')
