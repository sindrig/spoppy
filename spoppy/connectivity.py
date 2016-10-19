import socket
import time

REMOTE_SERVER = 'www.google.com'

def check_internet_connection():
    print ("Checking for internet connection.")
    connected = False
    while not connected:
        try:
            s = socket.create_connection((REMOTE_SERVER, 80), 2)
            connected = True
        except:
            print ("Not connected to the internet - waiting for 10 seconds.")
            time.sleep(10)
            connected = False
    print("Connected to the internet - continuing normal program flow. ")


if __name__ == '__main__':
    check_internet_connection()