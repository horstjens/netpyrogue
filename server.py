import os
import random
import sys
import time
from weakref import WeakKeyDictionary

from lib.PodSixNet_Library.Channel import Channel
from lib.PodSixNet_Library.Server import Server

global running
running = True


class Item:
    id = 0

    def __init__(self):
        self.id = Item.id
        Item.id += 1

        ClientChannel.items[self.id] = self

        # Type?

        self.name = random.choice(("Destruktive Zerstörungsenergie", "deaktivierte Netzwerkkarte", "GNU Lizenzbrief",
                                   "Metasploit", "Rubber Ducky", "USB Rubber Ducky"))
        self.playerInventoryChar = ''
        self.isEquipped = False
        self.char = "*"

        self.z = 0
        self.x = 0
        self.y = 0

        while ClientChannel.wall_check(0, self.x, self.y, self.z):
            self.z = random.randint(0, len(ClientChannel.dungeon) - 1)
            self.y = random.randint(1, len(ClientChannel.dungeon[self.z]) - 1)
            self.x = random.randint(1, len(ClientChannel.dungeon[self.z][-1]) - 1)

        # self.z = len(ClientChannel.dungeon)
        # print("z: " + str(self.z))
        # self.y = len(ClientChannel.dungeon[self.z - 1])
        # print("y: " + str(self.y))
        # self.x = len(ClientChannel.dungeon[self.z - 1][-1])
        # print("x: " + str(self.x))
        print("[Server] Produced \"" + self.name + "\" at z:" + str(self.z) + ", y:" + str(self.y) + ", x:" + str(
                self.x) + ".")

    def pickup(self, playerchar):
        self.playerInventoryChar = playerchar
        self.x = None
        self.y = None
        self.z = None

    def drop(self, x, y, z):
        self.playerInventoryChar = ''
        self.x = x
        self.y = y
        self.z = z


def get_items_at(x, y, z):
    retItems = []
    for item in ClientChannel.items.values():
        if item.playerInventoryChar != '':
            continue
        if item.x == x and item.y == y and item.z == z:
            retItems.append(item)
    if len(retItems) == 0:
        return False
    return retItems


class ClientChannel(Channel):
    """Game client representation"""

    free_x = 1

    items = {}

    dungeon = []

    movings = {
        1: (0, -1),
        2: (1, -1),
        3: (1, 0),
        4: (1, 1),
        5: (0, 1),
        6: (-1, 1),
        7: (-1, 0),
        8: (-1, -1)
    }

    # free_y = 0 # Maps werden circa 80 x lang sein, free_y wird gerade nicht gebraucht

    def __init__(self, *args, **kwargs):
        # If there are to many users which did not yet
        # enter a username (= anonymous) | Random: v v v v v v v
        self.player_name = "anonymous" + str(random.randrange(0, 101, 2))

        self.id = ClientChannel.free_x
        self.x = ClientChannel.free_x
        self.y = 2
        self.z = 0
        ClientChannel.free_x += 1

        # self._server.time_last_move[self.id] = time.time()

        # self.y = self.free_y
        # ClientChannel.free_y += 1

        self.char = chr(self.x + 96)  # Ascii char code (97 - 172 = a - z)

        self.inventory = {"Mysterious book": 1}
        self.hp = 100

        Channel.__init__(self, *args, **kwargs)
        self._server.time_last_move[self.id] = time.time()

    def Close(self):
        print("[Server] Player \"" + self.player_name + "\" disconnected.")
        self._server.delete_player(self)

    # Network specific callbacks

    def Network_chat(self, data):
        message = data['chat']
        message = message[1:]
        print("[Server] Player \"" + self.player_name + "\" sent chat message \"" + message + "\".")
        self._server.send_to_all({"action": "chat", "chat": message, "who": self.player_name})

    # Will be called when the player enters his nickname ==> PLAYERJOIN
    def Network_nickname(self, data):
        self.player_name = data['player_name']
        self._server.publish_players()
        self.Network_playerjoin()

    def Network_playerjoin(self):
        print("[Server] Player \"" + self.player_name + "\" joined the game.")
        self._server.send_to_all({"action": "playerjoin", "player_name": self.player_name})

    def Network_playermove(self, data):
        if not self._server.can_move(self.id):
            self.Send({"action": "system_message", "message": "You can not move yet"})
            return

        print("[Server] Player \"" + self.player_name + "\" moved to Direction \"" + str(data['direction']) + "\".")

        dx, dy = ClientChannel.movings[data['direction']]
        if self.wall_check(self.x + dx, self.y + dy, self.z):
            self.Send({"action": "system_message", "message": "You bumped into the incredible wall."})
            dx, dy = 0, 0
        if self.player_check(self.x + dx, self.y + dy, self.z):
            self.Send({"action": "system_message", "message": "You bumped into the other player, he hates ya now."})
            dx, dy = 0, 0
        if get_items_at(self.x + dx, self.y + dy, self.z):
            items = get_items_at(self.x + dx, self.y + dy, self.z)
            for item in items:
                item.pickup(self.char)
                self.Send({"action": "system_message", "message": "You found a: {}.".format(item.name)})

        print("Spieler: " + str(len(self._server.players)))

        # self.x += -dx
        # self.y += -dy
        self.x += dx
        self.y += dy

        print("[Server] Player \"" + self.player_name + "\" got new coordinates. dx: " + str(dx) + ", dy: " + str(dy),
              "x: " + str(self.x) + ", y: " + str(self.y) + ", z: " + str(self.z))
        self._server.moved(self.id)

    def Network_request_cords(self, data):
        print("[Server] Player \"" + self.player_name + "\" requested coordinates.")
        self.Send({"action":       "got_cords",
                   "x_cordinates": [p.x for p in self._server.players if p.player_name == self.player_name],
                   "y_cordinates": [p.y for p in self._server.players if p.player_name == self.player_name],
                   })

    def Network_request_dungeon(self, data):
        print("[Server] Player \"" + self.player_name + "\" requested the dungeon.")
        the_dungeon = []

        # for line in self.dungeon:
        #    for char in line:
        #        print(char, end="")
        #    print()

        for line in self.get_player_dungeon():
            line2 = []
            for char in line:
                line2.append(char)
            the_dungeon.append(line2)
        for item in ClientChannel.items.values():
            if item.z == self.z and item.playerInventoryChar == '':
                the_dungeon[item.y][item.x] = item.char
        for player in self._server.players:
            the_dungeon[player.y][player.x] = player.char

        # self.Send({"action": "got_dungeon", "the_dungeon": the_dungeon})
        self._server.send_to_all({"action": "got_dungeon", "the_dungeon": the_dungeon})

    def wall_check(self, x, y, z):
        return ClientChannel.dungeon[z][y][x] == "#"

    def player_check(self, x, y, z):
        for player in self._server.players:
            if player.char != self.char:
                if player.x == x and player.y == y and player.z == z:
                    return True
        return False

    def get_player_dungeon(self):
        return ClientChannel.dungeon[self.z]

    def send_system_message(self, message):
        self.Send({"action": "system_message", "message": message})

    def send_server_message(self, message):
        self.Send({"action": "server_message", "message": message})

    def Network_request_inventory(self, data):
        # items = [item for item in ClientChannel.items.values() if item.playerInventoryChar == self.char] # Kann
        # keine Objekte senden

        items = [(item.id, item.name) for item in ClientChannel.items.values() if item.playerInventoryChar == self.char]
        print(("Player \"{}\" requested his inventory: " + str(items)).format(self.player_name))
        self.Send({"action": "got_inventory", "inventory": items})

    def Network_drop(self, data):
        print("Player " + self.player_name + " tried to drop item " + str(data['item']))
        items = [item.id for item in ClientChannel.items.values() if item.playerInventoryChar == self.char]
        print("Player " + self.player_name + " inventory: " + str(items))
        item_id = data['item']
        if item_id not in items:
            print(str(item_id) + "not in " + str(items))
            self.Send({"action": "system_message", "message": "You don't own item nr. " + str(item_id) + "! mount "
                                                                                                         "/dev/brain!"})
            return
        ClientChannel.items[item_id].drop(self.x, self.y, self.z)


class GameServer(Server):
    channelClass = ClientChannel

    def __init__(self, *args, **kwargs):
        Server.__init__(self, *args, **kwargs)
        self.time_last_move = {}
        self.players = WeakKeyDictionary()
        print("[Server] Server launched")

    def Connected(self, channel, addr):
        self.add_player(channel)

    def add_player(self, player):
        print("[Server] New Player" + str(player.addr))
        self.players[player] = True
        # self.publish_players()

        print("[Server] players", [p for p in self.players])

    def moved(self, id):
        self.time_last_move[id] = time.time()

    def can_move(self, id):
        if len(self.players) == 1:
            return True
        return time.time() - self.time_last_move[id] > 0

    def delete_player(self, player):
        print("[Server] Deleting Player" + str(player.addr))
        del self.players[player]
        self.publish_players()

    def publish_players(self):
        self.send_to_all({"action": "players", "players": [p.player_name for p in self.players]})

    def send_to_all(self, data):
        [player.Send(data) for player in self.players]

    def launch_server(self):
        global running
        while running:
            self.Pump()
            try:
                time.sleep(0.0001)
            except KeyboardInterrupt:
                print("Caught [SIGTERM] (KeyboardInterrupt)\nExiting...")
                running = False


if __name__ == '__main__':

    # get command line argument of server, port
    if len(sys.argv) != 2:
        print("[Server] Usage:", sys.argv[0], "host:port")
        print("[Server] e.g.", sys.argv[0], "localhost:31425")
    else:

        print("Reading dungeons...")
        for filename in os.listdir("data/maps"):
            print("Found dungeon: " + filename)
            dungeon_content = open("data/maps/" + filename, "r").read()
            ClientChannel.dungeon.append(dungeon_content)

        for z, dungeon in enumerate(ClientChannel.dungeon):
            d = []
            for line in dungeon.splitlines():
                d.append(list(line))
            ClientChannel.dungeon[z] = d

        for x in range(100):
            Item()
        # print(ClientChannel.items)
        host, port = sys.argv[1].split(":")
        s = GameServer(localaddr=(host, int(port)))

        # dungeon = ClientChannel.dungeon
        # d = []

        # for line in dungeon.splitlines():
        #    d.append(list(line))

        # ClientChannel.dungeon = d

        s.launch_server()