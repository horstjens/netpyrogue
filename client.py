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
        self.equipped_items = {}
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
            elif input_string.split(" ")[0] == "drop":
                try:
                    id = int(input_string.split(" ")[1])
                except Exception:
                    print("mount /dev/brain")
                    return
                connection.Send({"action": "drop", "item": id})
            elif input_string.startswith("w"):
                print("Going north")
                for i in range(input_string.count("w", 0, len(input_string))):
                    self.sendMove(Directions.North.value)
            elif input_string.startswith("a"):
                print("Going west")
                for i in range(input_string.count("a", 0, len(input_string))):
                    self.sendMove(Directions.West.value)
            elif input_string.startswith("s"):
                print("Going south")
                for i in range(input_string.count("s", 0, len(input_string))):
                    self.sendMove(Directions.South.value)
            elif input_string.startswith("d"):
                print("Going east")
                for i in range(input_string.count("d", 0, len(input_string))):
                    self.sendMove(Directions.East.value)
            elif input_string == "i":
                print("Your inventory:")
                for item in self.inventory:
                    print("- {}: {}".format(item[0], item[1]))
            else:
                print("[System] Unrecognized input: " + input_string)

    # Network event/chat callbacks

    def Network_got_cords(self, data):
        cordinates = data['x_cordinates'], data['y_cordinates']

    def Network_got_inventory(self, data):
        self.inventory = data['inventory']

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
        global running
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