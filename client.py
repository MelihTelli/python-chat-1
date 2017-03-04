from asyncio import QueueEmpty
from queue import Queue
import tkinter as tk
from tkinter import messagebox
import threading
import socket
import re

HOST = 'localhost'
PORT = 1234

queue = Queue()
root = None
myapp = None

class Receiver(threading.Thread):
    def __init__(self, conn):
        threading.Thread.__init__(self)
        self.sock = conn

    def run(self):
        msg = ""
        while 1:
            try:
                tmp = self.sock.recv(1024)
            except:
                self.sock.close()
                queue.put('QUIT')
                break
            if not tmp:
                self.sock.close()
                queue.put('QUIT')
                break
            msg += tmp.decode()
            s = msg.split('\n')
            for m in s[:-1]:
                queue.put(m)
                if m == 'QUIT':
                    self.sock.close()
                    return
            msg = s[-1]


class ChatWindow:
    def __init__(self, root, sock, login):
        self.sock = sock

        root.minsize(500, 500)
        root.protocol('WM_DELETE_WINDOW', self.quit)

        self.mainFrame = tk.Frame(root)
        self.mainFrame.grid(row=0, column=0, sticky=tk.N + tk.S + tk.W + tk.E)

        self.chat = tk.Text(self.mainFrame, width=1, height=1)
        self.chat.grid(column=0, row=0, sticky=tk.N + tk.S + tk.W + tk.E)
        self.chat.tag_configure('head1', background='#F1F3F2',
                                font=('Verdana', 10, 'bold'))
        self.chat.tag_configure('head2', background='#BEBEBE',
                                font=('Verdana', 10, 'bold'))
        self.chat.tag_configure('nick1', background='#F1F3F2', foreground='#483FFF',
                                font=('Verdana', 10, 'bold'))
        self.chat.tag_configure('nick2', background='#BEBEBE', foreground='#483FFF',
                                font=('Verdana', 10, 'bold'))
        self.chat.tag_configure('text1', background='#F1F3F2', font=('Verdana', 10, ''),
                                spacing1=10, spacing3=10, borderwidth=50)
        self.chat.tag_configure('text2', background='#BEBEBE', font=('Verdana', 10, ''),
                                spacing1=10, spacing3=10)
        self.chat.config(state=tk.DISABLED)
        self.messages_count = 0

        self.listbox = tk.Listbox(self.mainFrame,)
        self.listbox.grid(column=1, row=0, rowspan=2, sticky=tk.N + tk.S + tk.W + tk.E)
        self.listbox.insert(tk.END, "ALL")
        self.listbox.select_set(0)
        self.listbox.event_generate("<<ListboxSelect>>")

        self.message_box = tk.Text(self.mainFrame, width=1, height=1)
        self.message_box.grid(column=0, row=1, sticky=tk.N + tk.S + tk.W + tk.E)
        self.message_box.bind('<Return>', lambda ev: self.send_message())

        self.button_send = tk.Button(self.mainFrame, text="Send Message", command=self.send_message)
        self.button_send.grid(column=0, row=2, columnspan=1, sticky=tk.N + tk.S + tk.W + tk.E)
        self.button_send.bind('<Return>', lambda ev: self.send_message())

        self.button_exit = tk.Button(self.mainFrame, text="Exit", command=self.quit)
        self.button_exit.grid(column=1, row=2, columnspan=1, sticky=tk.N + tk.S + tk.W + tk.E)

        self.mainFrame.rowconfigure(0, weight=4)
        self.mainFrame.rowconfigure(1, weight=2)
        self.mainFrame.rowconfigure(2, weight=1)

        self.mainFrame.columnconfigure(0, weight=3)
        self.mainFrame.columnconfigure(1, weight=1)

        self.clients_list = ['ALL']

        self.nick = login
        root.title("Chat - {}".format(self.nick))

    def quit(self):
        self.sock.send('LOGOUT\n'.encode())

    def send_message(self):
        if len(self.listbox.curselection()) < 1:
            messagebox.showinfo("No receiver", "Select the receiver...")
            return 'break'
        to = self.clients_list[self.listbox.curselection()[0]]
        msg = self.message_box.get('1.0', tk.END).strip()
        if msg == "":
            messagebox.showinfo("Empty message", "The message is empty...")
            return 'break'
        self.sock.send('MSG;{};{}\n'.format(to, msg).encode())
        self.message_box.delete('1.0', tk.END)
        self.render_message(self.nick, to, msg)
        return 'break'

    def list(self, str):
        for k in str.split(';')[1:]:
            if k == "" or k == self.nick:
                continue
            self.listbox.insert(tk.END, k)
            self.clients_list.append(k)

    def render_message(self, fr, to, msg):
        self.chat.config(state=tk.NORMAL)
        t = '2'
        if self.messages_count % 2 == 0:
            t = '1'
        tag = 'head'
        if fr == self.nick:
            tag = 'nick'
        self.chat.insert(tk.END, fr, tag+t)
        self.chat.insert(tk.END, ' → ', 'head'+t)
        tag = 'head'
        if to == self.nick:
            tag = 'nick'
        self.chat.insert(tk.END, '{}\n'.format(to), tag+t)
        self.chat.insert(tk.END, '{}\n'.format(msg), 'text'+t)
        self.chat.config(state=tk.DISABLED)
        self.messages_count += 1

    def msg(self, str):
        str = str.split(';')
        fr = str[1]
        to = str[2]
        msg = str[3]
        self.render_message(fr, to, msg)

    def login(self, str):
        str = str.split(';')[1]
        self.listbox.insert(tk.END, str)
        self.clients_list.append(str)

    def logout(self, str):
        str = str.split(';')[1]
        for i in range(len(self.clients_list)):
            if self.clients_list[i] == str:
                self.listbox.delete(i)
                break
        self.clients_list.remove(str)

class LoginWindow:
    def __init__(self, sock):
        self.root = root
        self.sock = sock
        self.nick = ""
        self.mainFrame = tk.Frame(root)
        self.mainFrame.grid(row=0, column=0, sticky=tk.N + tk.S + tk.W + tk.E)
        login_label = tk.Label(self.mainFrame, text="Login: ")
        login_label.grid(row=0, column=0, sticky=tk.W + tk.E, padx=20, pady=20)
        self.login_entry = tk.Entry(self.mainFrame)
        self.login_entry.grid(row=0, column=1, sticky=tk.W + tk.E, padx=20, pady=20)
        self.login_entry.bind('<Return>', lambda ev: self.login())
        login_button = tk.Button(self.mainFrame, text="Login!", command=self.login)
        login_button.grid(row=1, column=0, columnspan=2, sticky=tk.W + tk.E, padx=20, pady=20)

        self.mainFrame.rowconfigure(0, weight=1)
        self.mainFrame.rowconfigure(1, weight=1)

        self.mainFrame.columnconfigure(0, weight=0)
        self.mainFrame.columnconfigure(1, weight=1)

    def login(self):
        if not re.match('[a-zA-Z0-9]+$', self.login_entry.get()):
            messagebox.showinfo('Invalid login', 'Invalid login!')
            return
        self.sock.send('LOGIN;{}\n'.format(self.login_entry.get()).encode())
        self.nick = self.login_entry.get()

    def login_ok(self):
        global myapp
        self.mainFrame.destroy()
        myapp = ChatWindow(self.root, self.sock, self.nick)

def periodicCall():
    while not queue.empty():
        try:
            q = queue.get_nowait()
            if q == 'LOGINOK':
                myapp.login_ok()
            elif q == 'LOGINDUPL':
                messagebox.showinfo('Login', 'Login already in use')
            elif q == 'QUIT':
                root.destroy()
            elif re.match('LIST;.*', q):
                myapp.list(q)
            elif re.match('MSG;.*;.*', q):
                myapp.msg(q)
            elif re.match('LOGIN;.*', q):
                myapp.login(q)
            elif re.match('LOGOUT;.*', q):
                myapp.logout(q)
        except QueueEmpty:
            break
    root.after(200, periodicCall)

def init():
    global root
    global myapp
    root = tk.Tk()
    root.title("Chat - login")
    root.minsize(200, 200)
    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST, PORT))
    except:
        messagebox.showerror('Error', 'Can\'t connect with the server!')
        root.destroy()
        return
    myapp = LoginWindow(sock)
    Receiver(sock).start()
    periodicCall()

init()
root.mainloop()