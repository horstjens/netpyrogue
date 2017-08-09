import sys
from _thread import start_new_thread
from sys import stdin
from time import sleep

from Directions import Directions
from lib.PodSixNet_Library.Connection import connection, ConnectionListener

global debug
debug = False
global running
running = True


class Client(ConnectionListener):
    def __init__(self, host, port):
        self.player_name = None
        self.Connect((host, port))
        print("Enter your nickname: ")
        player_name = stdin.readline().rstrip("\n")
        connection.Send({"action": "nickname", "player_name": player_name})
        self.inventory = {}
        self.equipped_items= {}
        t = start_new_thread(self.InputLoop, ())

    def ClientGameLoop(self):
        connection.Pump()
        self.Pump()

    def InputLoop(self):
        # continually reads from stdin and sends whatever is typed to the server
        while True:
            connection.Send({"action": "request_cords", "abc": "xyz"})
            connection.Send({"action": "request_dungeon", "abc": "xyz"})
            connection.Send({"action": "request_inventory", "abc": "xyz"})
            input_string = stdin.readline().rstrip("\n")
            print("Input: " + input_string)
            if input_string.startswith("!"):
                connection.Send({"action": "chat", "chat": input_string})
            elif input_string == "w":
                print("Going north")
                self.sendMove(Directions.North.value)
            elif input_string == "a":
                print("Going west")
                self.sendMove(Directions.West.value)
            elif input_string == "s":
                print("Going south")
                self.sendMove(Directions.South.value)
            elif input_string == "d":
                print("Going east")
                self.sendMove(Directions.East.value)
            elif input_string == "i":
                print("Your inventory:")
                for item in self.inventory:
                    print("- {}".format(item))
                print("You have these items equipped:")
                for item in self.equipped_items:
                    print("- {}".format(item))
            else:
                print("[System] Unrecognized input: " + input_string)

    # Network event/chat callbacks

    def Network_got_cords(self, data):
        cordinates = data['x_cordinates'], data['y_cordinates']

    def Network_got_inventory(self, data):
        self.inventory = data['inventory']
        self.equipped_items = data['equipped_items']

    def Network_got_dungeon(self, data):
        d = data['the_dungeon']
        for line in d:
            for char in line:
                print(char, end="")
            print()
            # print("Dungeon:\n" + data['the_dungeon'])

    def Network_players(self, data):
        if debug:
            print("[Debug] *** players: " + ", ".join([p for p in data['players']]))
            # Any players named "anonymous" have not entered a player_name yet

    def Network_system_message(self, data):
        print("[System] " + data['message'])

    # def Network_server_data(self,data):#call(data['message'])

    def Network_server_message(self, data):
        print("[Server] " + data['message'])

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
            try:
                sleep(0.001)
            except KeyboardInterrupt:
                print("[System] Quitting...")
                running = False
                break
        print("Lost connection to server")
