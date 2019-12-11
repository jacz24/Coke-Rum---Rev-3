from holdem import Table, TableProxy, PlayerControl, PlayerControlProxy
import time

seats = 8
# start an table with 8 seats
t = Table(seats)
tp = TableProxy(t)

# controller for human meat bag
h = PlayerControl("localhost", 8001, 1, False, None)
hp = PlayerControlProxy(h)

print('starting ai players')

#rule based ai

ai = PlayerControl("localhost", 8002, 2, True, 3)
aip = PlayerControlProxy(ai)

# fill the rest of the table with ai players
for i in range(3,seats+1):
    p = PlayerControl("localhost", 8000+i, i, True, 0)
    pp = PlayerControlProxy(p)

tp.run_game()
