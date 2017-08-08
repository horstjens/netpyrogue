import random
import sys
from time import sleep
from weakref import WeakKeyDictionary

from PodSixNet.Channel import Channel
from PodSixNet.Server import Server


class ClientChannel(Channel):
    """Game client representation"""

    free_x = 1

    dungeon = """
####################################################
#..................................................#
#..................................................#
#..................................................#
#..................................................#
#..................................................#
#..................................................#
#..................................................#
#..................................................#
#..................................................#
#..................................................#
#..................................................#
#..................................................#
#..................................................#
####################################################
"""

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
        self.x = ClientChannel.free_x
        self.y = 2
        ClientChannel.free_x += 1
        self.char = str(self.x)
        # self.y = self.free_y
        # ClientChannel.free_y += 1

        Channel.__init__(self, *args, **kwargs)

    def Close(self):
        print("[Server] Player \"" + self.player_name + "\" disconnected.")
        self._server.DelPlayer(self)

    # Network specific callbacks

    def Network_chat(self, data):
        print("[Server] Player \"" + self.player_name + "\" sent chat message \"" + data['chat'] + "\".")
        self._server.SendToAll({"action": "chat", "chat": data['chat'], "who": self.player_name})

    # Will be called when the player enters his nickname ==> PLAYERJOIN
    def Network_nickname(self, data):
        self.player_name = data['player_name']
        self._server.publish_players()
        self.Network_playerjoin()

    def Network_playerjoin(self):
        print("[Server] Player \"" + self.player_name + "\" joined the game.")
        self._server.SendToAll({"action": "playerjoin", "player_name": self.player_name})

    def Network_playermove(self, data):
        print("[Server] Player \"" + self.player_name + "\" moved to Direction \"" + str(data['direction']) + "\".")

        dx, dy = ClientChannel.movings[data['direction']]
        if self.wallcheck(self.x + dx, self.y + dy):
            dx, dy = 0, 0
        # self.x += -dx
        # self.y += -dy
        self.x += dx
        self.y += dy

        print("[Server] Player \"" + self.player_name + "\" got new coordinates. dx: " + str(dx) + ", dy: " + str(dy),
              "x: " + str(self.x) + ", y: " + str(self.y))

    def Network_request_cords(self, data):
        print("[Server] Player \"" + self.player_name + "\" requested coordinates.")
        self.Send({"action": "got_cords",
                   "x_cordinates": [p.x for p in self._server.players if p.player_name == self.player_name],
                   "y_cordinates": [p.y for p in self._server.players if p.player_name == self.player_name],
                   })

    def Network_request_dungeon(self, data):
        print("[Server] Player \"" + self.player_name + "\" requested the dungeon.")
        self.the_dungeon = []

        #for line in self.dungeon:
        #    for char in line:
        #        print(char, end="")
        #    print()

        for line in self.dungeon:
            line2 = []
            for char in line:
               line2.append(char)
            self.the_dungeon.append(line2)
        for p in self._server.players:
            self.the_dungeon[p.y][p.x] = p.char

        self._server.SendToAll({"action": "got_dungeon", "the_dungeon": self.the_dungeon})

    def wallcheck(self, x, y, z=0):
        target = ClientChannel.dungeon[y][x]
        return target == "#"


class GameServer(Server):
    channelClass = ClientChannel

    def __init__(self, *args, **kwargs):
        Server.__init__(self, *args, **kwargs)
        self.players = WeakKeyDictionary()
        print("[Server] Server launched")

    def Connected(self, channel, addr):
        self.AddPlayer(channel)

    def AddPlayer(self, player):
        print("[Server] New Player" + str(player.addr))
        self.players[player] = True
        # self.publish_players()
        print("[Server] players", [p for p in self.players])

    def DelPlayer(self, player):
        print("[Server] Deleting Player" + str(player.addr))
        del self.players[player]
        self.publish_players()

    def publish_players(self):
        self.SendToAll({"action": "players", "players": [p.player_name for p in self.players]})

    def SendToAll(self, data):
        [player.Send(data) for player in self.players]

    def Launch(self):
        while True:
            self.Pump()
            sleep(0.0001)


if __name__ == '__main__':
    # get command line argument of server, port
    if len(sys.argv) != 2:
        print("[Server] Usage:", sys.argv[0], "host:port")
        print("[Server] e.g.", sys.argv[0], "localhost:31425")
    else:
        host, port = sys.argv[1].split(":")
        s = GameServer(localaddr=(host, int(port)))

        dungeon = ClientChannel.dungeon
        d = []

        for line in dungeon.splitlines():
            d.append(list(line))

        ClientChannel.dungeon = d

        s.Launch()
