import os
import random
import sys
import time
from weakref import WeakKeyDictionary

from Directions import Directions
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

        self.name = random.choice(("destructive destruction energy", "disabled network card", "GNU license letter",
                                   "exploitation framework", "Debug Rubber Ducky", "USB Rubber Ducky"))
        self.playerInventoryChar = ''
        self.isEquipped = False
        self.char = "*"

        self.z = 0
        self.x = 0
        self.y = 0

        for i in range(1000):
            self.z = random.randint(0, len(ClientChannel.dungeon) - 1)
            self.y = random.randint(1, len(ClientChannel.dungeon[self.z]) - 1)
            self.x = random.randint(1, len(ClientChannel.dungeon[self.z][-1]) - 1)
            if not ClientChannel.wall_check(0, self.x, self.y, self.z) \
                    and not ClientChannel.staircase_check(0, self.x, self.y, self.z):
                break
        else:
            print("Couldn't find appropriate place for " + self.name + ", is the dungeon too small?")

        print("[Server] Produced item \"" + self.name + "\" at z:" + str(self.z) + ", y:" + str(self.y) + ", x:" + str(
                self.x) + ".")

    def pickup(self, player_character):
        self.playerInventoryChar = player_character
        self.x = None
        self.y = None
        self.z = None

    def drop(self, x, y, z):
        self.playerInventoryChar = ''
        self.x = x
        self.y = y
        self.z = z


def get_items_at(x, y, z):
    return_items = []
    for item in ClientChannel.items.values():
        if item.playerInventoryChar != '':
            continue
        if item.x == x and item.y == y and item.z == z:
            return_items.append(item)
    if len(return_items) == 0:
        return False
    return return_items


class ClientChannel(Channel):
    """Game client representation"""

    free_x = 1

    items = {}

    dungeon = []

    player_movements = {
        1: (0, -1),
        2: (1, -1),
        3: (1, 0),
        4: (1, 1),
        5: (0, 1),
        6: (-1, 1),
        7: (-1, 0),
        8: (-1, -1)
    }

    # free_y = 0 # Maps will be at least 80 tiles long at the x-axis, free_y is not currently important

    def __init__(self, *args, **kwargs):
        print("[Server] Initializing player...")
        # If there are to many users which did not yet
        # enter a username (= anonymous) | Random: v v v v v v v
        self.player_name = "anonymous" + str(random.randrange(0, 101, 2))

        self.user_agent = "undefined"

        self.id = ClientChannel.free_x
        self.x = ClientChannel.free_x
        self.y = 2
        self.z = 0
        ClientChannel.free_x += 1

        # self._server.time_last_move[self.id] = time.time()

        # self.y = self.free_y
        # ClientChannel.free_y += 1

        self.char = chr(self.x + 96)  # Ascii char code (97 - 172 = a - z)

        self.hp = 100
        print("[Server] Player initialized with char \"" + self.char + "\".")
        Channel.__init__(self, *args, **kwargs)
        self._server.time_last_move[self.id] = time.time()

    def Close(self):
        print("[Server] Player \"" + self.player_name + "\" (\"" + self.char + "\") disconnected.")
        self._server.delete_player(self)

    # Network specific callbacks

    def Network_chat(self, data):
        message = data['chat']
        message = message[1:]
        print("[Server] Player \"" + self.player_name + "\" sent chat message \"" + message + "\".")
        self._server.send_to_all({"action": "chat", "chat": message, "who": self.player_name})

    def Network_useragent(self, data):
        self.user_agent = data['agent_string']
        print("[Server] Player ID: " + str(self.id) + " connected using \"" + self.user_agent + "\".")

    def Network_nickname(self, data):
        if self.user_agent != "undefined":
            for p in self._server.players:
                if p.player_name.lower() == data['player_name'].lower():
                    self.Send({"action": "system_message", "message": "There's already another player with this name."})
                    self.Send({"action": "system_message", "message": "//faker"})
                    self.Close()
                    self.close()
                    self.close_when_done()
                    return
            self.player_name = data['player_name']
            self._server.publish_players()
            self.Network_playerjoin()
        else:
            print("[Server] Player ID: " + str(self.id) + " sent a username (\"" + data['player_name'] + "\") before "
                                                                                                         "sending his "
                                                                                                         "useragent!")
            self.Close()
            self.close()
            self.close_when_done()

    def Network_playerjoin(self):
        print("[Server] Player \"" + self.player_name + "\" joined the game.")
        self._server.send_to_all({"action": "playerjoin", "player_name": self.player_name})

    def Network_playermove(self, data):
        if not self._server.can_move(self.id):
            self.Send({"action": "system_message", "message": "You can not move yet."})
            return

        print("[Server] Player \"" + self.player_name + "\" moved to Direction \"" + Directions(
                data['direction']).name + "\".")

        dx, dy = ClientChannel.player_movements[data['direction']]
        if self.wall_check(self.x + dx, self.y + dy, self.z):
            self.Send({"action": "system_message", "message": "You bumped into the incredible wall."})
            dx, dy = 0, 0
        elif self.player_check(self.x + dx, self.y + dy, self.z):
            self.Send({"action": "system_message", "message": "You bumped into the other player, he hates ya now."})
            dx, dy = 0, 0
        elif get_items_at(self.x + dx, self.y + dy, self.z):
            items = get_items_at(self.x + dx, self.y + dy, self.z)
            for item in items:
                item.pickup(self.char)
                self.Send({"action": "system_message", "message": "You found a: {}.".format(item.name)})
        elif self.staircase_check(self.x + dx, self.y + dy, self.z):
            if ClientChannel.dungeon[self.z][self.y + dy][self.x + dx] == "/":
                print("Player \"" + self.player_name + "\" walked a staircase up, is now at z: " + str(self.z) + ".")
                self.Send({"action": "system_message", "message": "You walked the stair up"})
                self.z += 1
            elif ClientChannel.dungeon[self.z][self.y + dy][self.x + dx] == "\\":
                print("Player \"" + self.player_name + "\" walked a staircase down, is now at z: " + str(self.z) + ".")
                self.Send({"action": "system_message", "message": "You walked the stair down"})
                self.z -= 1
            self.update_dungeon_for_players()

        # print("Online players: " + str(len(self._server.players)))

        # self.x += -dx
        # self.y += -dy
        self.x += dx
        self.y += dy

        print("[Server] Player \"" + self.player_name + "\" got new coordinates. dx: " + str(dx) + ", dy: " + str(dy),
              "x: " + str(self.x) + ", y: " + str(self.y) + ", z: " + str(self.z))
        self._server.player_moved(self.id)

    def Network_request_cords(self, data):
        print("[Server] Player \"" + self.player_name + "\" requested coordinates.")
        self.Send({"action":       "got_cords",
                   "x_coordinates": [p.x for p in self._server.players if p.player_name == self.player_name],
                   "y_coordinates": [p.y for p in self._server.players if p.player_name == self.player_name],
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
            if player.z == self.z:
                the_dungeon[player.y][player.x] = player.char

        self.send_to_same_dungeon({"action": "got_dungeon", "the_dungeon": the_dungeon})

    def update_dungeon_for_players(self):
        print("[Server] Updating dungeons for players.")
        for connected_player in self._server.players:
            the_dungeon = []
            for line in connected_player.get_player_dungeon():
                line2 = []
                for char in line:
                    line2.append(char)
                the_dungeon.append(line2)
            for item in ClientChannel.items.values():
                if item.z == connected_player.z and item.playerInventoryChar == '':
                    the_dungeon[item.y][item.x] = item.char
            for player in connected_player._server.players:
                if player.z == connected_player.z:
                    the_dungeon[player.y][player.x] = player.char
            connected_player.Send({"action": "got_dungeon", "the_dungeon": the_dungeon})

    def wall_check(self, x, y, z):
        return ClientChannel.dungeon[z][y][x] == "#"

    def player_check(self, x, y, z):
        for player in self._server.players:
            if player.char != self.char:
                if player.x == x and player.y == y and player.z == z:
                    return True
        return False

    def staircase_check(self, x, y, z):
        return ClientChannel.dungeon[z][y][x] == "/" or ClientChannel.dungeon[z][y][x] == "\\"

    def get_player_dungeon(self):
        return ClientChannel.dungeon[self.z]

    def send_system_message(self, message):
        self.Send({"action": "system_message", "message": message})

    def send_server_message(self, message):
        self.Send({"action": "server_message", "message": message})

    def Network_request_inventory(self, data):
        # items = [item for item in ClientChannel.items.values() if item.playerInventoryChar == self.char] # Can't
        # send objects

        items = [(item.id, item.name) for item in ClientChannel.items.values() if item.playerInventoryChar == self.char]
        print(("[Server] Player \"{}\" requested his inventory: " + str(items)).format(self.player_name))
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

    def send_to_same_dungeon(self, data):
        [player.Send(data) for player in self._server.players if player.z == self.z]


class GameServer(Server):
    channelClass = ClientChannel

    def __init__(self, *args, **kwargs):
        Server.__init__(self, *args, **kwargs)
        self.time_last_move = {}
        self.players = WeakKeyDictionary()
        print("[Server] Server launched")

    def Connected(self, channel, address):
        self.add_player(channel)

    def add_player(self, player):
        print("[Server] New Player" + str(player.addr))
        self.players[player] = True
        # self.publish_players()

        print("[Server] players", [p for p in self.players])

    def player_moved(self, id):
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
        print("[Server] Reading dungeons...")
        for filename in os.listdir("data/maps"):
            print("[Server] Found dungeon: " + filename)
            dungeon_content = open("data/maps/" + filename, "r").read()
            ClientChannel.dungeon.append(dungeon_content)
        print("[Server] Read dungeons, reassembling them for code use...")
        for z, dungeon in enumerate(ClientChannel.dungeon):
            d = []
            for line in dungeon.splitlines():
                d.append(list(line))
            ClientChannel.dungeon[z] = d
        item_count = 100
        print("[Server] Reassembled dungeons, generating " + str(item_count) + " items...")
        for x in range(item_count):
            Item()
        # print(ClientChannel.items)
        print("[Server] Generated items, starting the game server...")
        host, port = sys.argv[1].split(":")
        s = GameServer(localaddr=(host, int(port)))

        # dungeon = ClientChannel.dungeon
        # d = []

        # for line in dungeon.splitlines():
        #    d.append(list(line))

        # ClientChannel.dungeon = d

        s.launch_server()