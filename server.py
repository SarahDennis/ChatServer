"""server.py

Author:              EJ Johnson & Sarah Dennis
Class:               CSI-235
Assignment:          Final Project
Date Assigned:       4/12/2018
Due Date:            4/26/2018 11:59 PM
 
Description:
Server side chat application
"""
import asyncio, random, argparse, struct, json, os, ssl

list_of_users = []
list_of_messages = []
list_of_writers = []
user_accepted = False
info = ""

#CHECK IF MESSAGE IS NULL
def handle_conversation(reader, writer):
    """Handle a conversation between the server and clients

    Args:
        reader: the data being sent from the client to the server
        writer: the data being sent from the server to the client
    """
    #copy history into list of messages
    list_of_messages = []
    if os.stat("history.txt").st_size == 0:
        f = open("history.txt", "r+")
        f.write('{"MESSAGES":[]}')
        f.close()
    f = open("history.txt", "r+")
    contents = f.read()
    contents = json.loads(contents)
    history_len = len(contents["MESSAGES"])
    for i in range (0,history_len):
        list_of_messages.append(contents["MESSAGES"][i])
    f.close()
    print("History restored.")
    
    while True:
        #check to see if user is connected, if so, read in data
        try:
            length = yield from reader.readexactly(4)
            len_int = struct.unpack("!I", length)[0]
            data = yield from reader.readexactly(len_int)
        except asyncio.IncompleteReadError:
            index = list_of_users.index(username)
            list_of_users.remove(username)
            del list_of_writers[index]
            msg_left = {"USERS_LEFT" : username}
            #tell other users when user has left
            for writer in list_of_writers:
                send_one_message(writer, msg_left)
            return
        else:
            client_data = json.loads(data)
            #first time connection
            if "USERNAME" in client_data:
                username = client_data['USERNAME']
                #check if username exists
                if username not in list_of_users:
                    list_of_writers.append(writer)
                    list_of_users.append(username)
                    user_accepted = True
                    info = "Welcome to the server, enjoy your stay."
                    #send welcome info
                    data_dict = {"USERNAME_ACCEPTED" : user_accepted, 
                        "INFO" : info, 
                        "USER_LIST" : list_of_users, 
                        "MESSAGES" : list_of_messages}
                    send_one_message(writer, data_dict)
                    #notify other users of new user
                    msg_joined = {"USERS_JOINED" : username}
                    for writer in list_of_writers:
                        data_dict = {"USERNAME_ACCEPTED" : user_accepted,
                            "INFO" : info, "USER_LIST" : list_of_users,
                            "MESSAGES" : list_of_messages}
                        send_one_message(writer, msg_joined)
                    print("New connection data sent.")
                else:
                    user_accepted = False
                    info = "Username already in use"
                    send_one_message(writer, data_dict)
            #read message from client
            if "MESSAGES" in client_data:
                messages = client_data['MESSAGES']
                for message in messages:
                    #check if message format is correct
                    if len(message) != 4:
                        error_dict = {"ERROR": "User not found."}
                        send_one_message(writer, error_dict)
                    else:
                        list_of_messages.extend(message)
                        #store message in history
                        f = open("history.txt","r+")
                        contents = f.read()
                        contents = json.loads(contents)
                        if message[1] == "ALL":
                            contents["MESSAGES"].append(message)
                        contents = json.dumps(contents)
                        f.seek(0)
                        f.truncate()
                        f.write(contents)
                        print("Messaged saved to history successfully")
                        f.close()
                        #check and send to destination
                        if message[1] == "ALL":
                            for writer in list_of_writers:
                                msg_to_dict = {"MESSAGES" : [message]}
                                send_one_message(writer, msg_to_dict)
                        else:
                            dest = message[1]
                            src = message[0]
                            if dest in list_of_users:
                                dest_index = list_of_users.index(dest)
                                src_index = list_of_users.index(src)
                                msg_to_dict = {"MESSAGES" : [message]}
                                send_one_message(list_of_writers[dest_index], msg_to_dict)
                                send_one_message(list_of_writers[src_index], msg_to_dict)
                            else:
                                #send error if @user does not exist
                                error_dict = {"ERROR": "User not found."}
                                send_one_message(writer, error_dict)

def send_one_message(writer, msg_dict):
    """Send a message to the client in form of a json string

    Args:
        writer: the given writer that the message is being sent to
        msg_dict(str): the json string message in the form of a dictionary 
    """
    msg_dict = json.dumps(msg_dict)
    msg_dict = msg_dict.encode("ascii")
    msg_len = len(msg_dict)
    msg_packed = struct.pack("!I", msg_len)
    writer.write(msg_packed)
    writer.write(msg_dict)
    print("MESSAGE DATA: ", msg_dict)
            
def parse_command_line(description):
    """Parse command line and return a socket address

    Args:
        description(str): part of the ArgumentParser

    Return:
        str: A tuple consiting of the host and port 
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('host', help='IP or hostname')
    parser.add_argument('-p', metavar='port', type=int, default=9000,
                        help='TCP port (default 7000)')
    args = parser.parse_args()
    address = (args.host, args.p)
    return address

if __name__ == '__main__':
    address = parse_command_line('asyncio server using callbacks')
    purpose = ssl.Purpose.CLIENT_AUTH
    context = ssl.create_default_context(purpose, cafile="ca.crt")
    context.load_cert_chain("localhost.pem")
    loop = asyncio.get_event_loop()
    coro = asyncio.start_server(handle_conversation, *address, ssl=context)
    server = loop.run_until_complete(coro)
    print('Listening at {}'.format(address))
    try:
        loop.run_forever()
    finally:
        server.close()
        loop.close()
