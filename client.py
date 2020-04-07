"""client.py

    Run python autograder.py

Author:              EJ Johnson & Sarah Dennis
Class:               CSI-235
Assignment:          Final Project
Date Assigned:       4/12/2018
Due Date:            4/26/2018 11:59 PM
 
Description:
Client side chat application

This code has been adapted from that provided by Prof. Joshua Auerbach: 

Champlain College CSI-235, Spring 2018
The following code was written by Joshua Auerbach (jauerbach@champlain.edu)
"""
import sys, argparse, time, json, struct, ssl, asyncio, datetime, ssl, os
from colorama import init
from colorama import Fore, Back, Style
BUFFER_SIZE = 1024

info = ""
list_of_users = []
class Client(asyncio.Protocol):

    def connection_made(self, transport):
        """Connect to the server using transport

        Args:
            transport: connection to the server
        """
        self.transport = transport 
        self.address = transport.get_extra_info('peername')
        print('Accepted connection from {}'.format(self.address))
        self.data = b""
        self.user = b""
        self.username = True
        
    def check_user_name(self, user=None):
        """Prompt user to enter a username when entering server

        Args:
            user(str): used to reprompt the user when username is invalid 
        """
        self.data = b''
        #reprompt user if username is invalid
        if user is None:
            user = input("Please enter your username: ")
        self.user = user
        user_dict = {"USERNAME" : self.user}
        user_dict = json.dumps(user_dict)
        user_dict = user_dict.encode('ascii')
        user_dict_len = len(user_dict)
        len_pack = struct.pack('!I', user_dict_len)
        #send valid username
        self.transport.write(len_pack + user_dict)   
    
    
    def data_received(self, data):
        """Identifies the data received from the server and prints to client

        Args:
            data(byte str): data being received from server 
        """
        global info
        global list_of_users
        self.data += data
        while True:
            #get first 4 bytes as length
            length = 4
            if len(self.data) < length:
                return
            len_int = struct.unpack("!I", self.data[:4])[0]
            if len(self.data[4:]) < len_int:
                return
            server_data = json.loads(self.data[4:len_int + 4])
            self.data = self.data[len_int + 4:]
            #check if username was accepted
            if "USERNAME_ACCEPTED" in server_data:
                self.username = server_data['USERNAME_ACCEPTED']
                if not server_data['USERNAME_ACCEPTED']:
                    print("That username is already in use")
                    print("Please enter your username: ")
                    return
            #print info message
            if "INFO" in server_data:
                info = server_data['INFO']
                print(info)
            if "USERS_JOINED" in server_data:
                print("User joined: ", server_data['USERS_JOINED'])
            if "USERS_LEFT" in server_data:
                print("User Left: ", server_data['USERS_LEFT'])
            if "USER_LIST" in server_data:
                list_of_users = server_data['USER_LIST']
                print("User List: ", end="")
                user_len = len(list_of_users)
                for i in range (0,user_len):
                    print(" ",list_of_users[i], end="")
                print("")
            if "MESSAGES" in server_data:
                msgs_count = len(server_data['MESSAGES'])
                for i in range (msgs_count):
                    new_data = server_data["MESSAGES"]
                    format_time = datetime.datetime.fromtimestamp(new_data[i][2]).strftime('%c') 
                    print("[" + format_time + "]", new_data[i][0] + " (@" + new_data[i][1] + "): ", new_data[i][3])
            if "ERROR" in server_data:
                print(server_data["ERROR"])
            
    def send_message(self, message):
        """Send a message to the server in given format

        Args:
            message(str): user input that is being sent to server
        """
        if not self.username:
            self.check_user_name(message)
            return
        epoch_time = int(time.time())
        if "@" in message:
            split_message = message.split(" ", 1)
            user_without_symbol = split_message[0]
            user_without_symbol = user_without_symbol[1:]
            if len(split_message) == 1:
                split_message.append("")
            full_message = (self.user, user_without_symbol, epoch_time, split_message[1])
        else:
            full_message = (self.user, "ALL", epoch_time, message)
        message_dict = {'MESSAGES': [full_message]}
        message_dict = json.dumps(message_dict)
        message_dict = message_dict.encode("ascii")
        msg_len = len(message_dict)
        msg_pack = struct.pack('!I', msg_len)
        self.transport.write(msg_pack + message_dict)
        
def launch_client(client, loop):
    """Continuously get input from user until exited

    Args:
        loop: asyncio get event loop function
    """
    client.check_user_name()
    print("To leave type 'exit'")
    while True:
        message = yield from loop.run_in_executor(None, input)
        if message == "exit":
            print("Exiting the server...")
            loop.stop()
            return 
        elif message == "clear":
            clear = lambda: os.system('cls')
            clear()
            print(info)
            print(list_of_users)
        else:
            client.send_message(message)

       
       
if __name__ == '__main__':
    description = 'asyncio server using callbacks'
    parser = argparse.ArgumentParser(description=description)
    purpose = ssl.Purpose.SERVER_AUTH
    context = ssl.create_default_context(purpose)
    parser.add_argument('host', help='IP or hostname')
    parser.add_argument('-p', metavar='port', type=int, default=9001,
                        help='TCP port (default 9000)')
    args = parser.parse_args()
    address = (args.host, args.p)

    loop = asyncio.get_event_loop()
    client = Client()
    coro = loop.create_connection(lambda: client, args.host, args.p, ssl=context)
    server = loop.run_until_complete(coro)
    
    asyncio.async(launch_client(client, loop))
    try:
        loop.run_forever()
    finally:
        loop.close()
        
    