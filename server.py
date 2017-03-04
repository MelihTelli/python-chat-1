from queue import Queue
import socket
import threading
import re

HOST = 'localhost'
PORT = 1234

queue = Queue()

class Server:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.bind((HOST, PORT))
        except:
            self.sock = None
            print("Canno t run server...")
            return
        self.sock.listen(5)
        self.clients = []
        ConnectionsListener(self).start()

    def run(self):
        if not self.sock:
            return
        while True:
            q, c = queue.get()
            if re.compile('LOGIN;.*').match(q):
                login = re.search('LOGIN;(.*)', q).group(1)
                for client in self.clients:
                    if login == client.login:
                        client.conn.send(b'LOGINDUPL\n')
                        break
                else:
                    for client in self.clients:
                        if c == client:
                            client.login = login
                            client.conn.send(b'LOGINOK\n')
                            self.send_logged_in_list(client)
                            self.client_logged_in(login)
                            break
            elif re.compile('MSG;.*;.*').match(q):
                target, msg = re.search('MSG;(.*);(.*)', q).groups()
                if target == 'ALL':
                    self.send_all(c, msg)
                else:
                    self.send_one(c, target, msg)
            elif q == 'LOGOUT':
                self.logout(c)
            elif q == 'QUIT':
                self.quit(c)

    def send_all(self, client, msg):
        for c in self.clients:
            if c == client:
                continue
            c.conn.send('MSG;{};ALL;{}\n'.format(client.login, msg).encode())

    def send_one(self, fr, to, msg):
        for c in self.clients:
            if to == c.login:
                c.conn.send('MSG;{};{};{}\n'.format(fr.login, to, msg).encode())

    def send_logged_in_list(self, client):
        client.conn.send(('LIST;' + ';'.join([x.login for x in self.clients]) + '\n').encode())

    def client_logged_in(self, login):
        for client in self.clients:
            if client.login == "" or client.login == login:
                continue
            client.conn.send('LOGIN;{}\n'.format(login).encode())

    def logout(self, client):
        client.conn.send('QUIT'.encode())
        client.conn.close()
        self.clients.remove(client)
        for c in self.clients:
            if c.login == "":
                continue
            c.conn.send('LOGOUT;{}\n'.format(client.login).encode())

    def quit(self, client):
        self.clients.remove(client)
        for c in self.clients:
            if c.login == "":
                continue
            c.conn.send('LOGOUT;{}\n'.format(client.login).encode())


class ConnectionsListener(threading.Thread):
    def __init__(self, server):
        threading.Thread.__init__(self)
        self.server = server

    def run(self):
        while 1:
            conn, addr = self.server.sock.accept()
            client = ClientThread(conn, addr, self.server)
            client.start()
            self.server.clients.append(client)

class ClientThread(threading.Thread):
    def __init__(self, conn, address, server):
        threading.Thread.__init__(self)
        self.conn = conn
        self.address = address
        self.server = server
        self.login = ""

    def run(self):
        text = ''
        while 1:
            try:
                tmp = self.conn.recv(1024)
            except:
                break
            if not tmp:
                break
            text += tmp.decode()
            s = text.split('\n')
            for t in s[:-1]:
                queue.put((t, self))
                if t == 'LOGOUT':
                    return
            text = s[-1]
        self.conn.close()
        queue.put(('QUIT', self))


server = Server()
server.run()
