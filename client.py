import sys
from _thread import start_new_thread
from sys import stdin
from time import sleep

from PodSixNet.Connection import connection, ConnectionListener

from Directions import Directions

global debug
debug = True
global running
running = True


class Client(ConnectionListener):
    def __init__(self, host, port):
        self.player_name = None
        self.Connect((host, port))
        print("Enter your nickname: ")
        player_name = stdin.readline().rstrip("\n")
        connection.Send({"action": "nickname", "player_name": player_name})
        # launch our threaded input loop
        t = start_new_thread(self.InputLoop, ())

    def ClientGameLoop(self):
        connection.Pump()
        self.Pump()

    def InputLoop(self):
        # continually reads from stdin and sends whatever is typed to the server
        while True:
            input_string = stdin.readline().rstrip("\n")
            print("Input: " + input_string)
            if input_string.startswith("!"):
                connection.Send({"action": "chat", "chat": input_string})
            elif input_string == "w":
                print("Going north")
                self.sendMove(Directions.North._value_)
            elif input_string == "a":
                print("Going west")
                self.sendMove(Directions.West._value_)
            elif input_string == "s":
                print("Going south")
                self.sendMove(Directions.South._value_)
            elif input_string == "d":
                print("Going east")
                self.sendMove(Directions.East._value_)
            else:
                print("[System] Unrecognized input: " + input_string)
            connection.Send({"action": "request_cords", "abc": "xyz"})
            connection.Send({"action": "request_dungeon", "abc": "xyz"})

    # Network event/chat callbacks

    def Network_got_cords(self, data):
        cordinates = data['x_cordinates'], data['y_cordinates']





    def Network_got_dungeon(self, data):
        d = data['the_dungeon']
        for line in d:
            for char in line:
                print(char, end="")
            print()
            # print("Dungeon:\n" + data['the_dungeon'])

    def Network_players(self, data):
        if debug:
            print("*** players: " + ", ".join([p for p in data['players']]))
            # Any players named "anonymous" have not entered a player_name yet

    def Network_chat(self, data):
        print("[Chat] " + data['who'] + ": " + data['chat'])

    def Network_playerjoin(self, data):
        print("[Server] Player " + data['player_name'] + " joined the game.")

    def Network_serverinfo(self, data):
        print("[Server] My infos...")

    def Network_error(self, data):
        print('[System] error: ', data['error'][1])
        connection.Close()

    def Network_disconnected(self, data):
        print('[System] Server disconnected')
        running = False

    def sendMove(self, direction):
        connection.Send({"action": "playermove", "direction": direction})


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage:", sys.argv[0], "host:port")
        print("e.g.", sys.argv[0], "localhost:31425")
    else:
        host, port = sys.argv[1].split(":")
        c = Client(host, int(port))
        print("[System] You are now connected to " + host + ":" + port + ".")
        while running:
            c.ClientGameLoop()
            sleep(0.001)
        print("Lost connection to server")
