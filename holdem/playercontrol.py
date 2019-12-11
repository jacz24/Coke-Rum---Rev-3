import numpy as np
import uuid
from threading import Thread

import xmlrpc.client
from xmlrpc.server import SimpleXMLRPCServer

from .holdemai import HoldemAI
from deuces.deuces import Card

# xmlrpc.client.Marshaller.dispatch[long] = lambda _, v, w: w("<value><i8>%d</i8></value>" % v)
# xmlrpc.client.Marshaller.dispatch[type(0)] = lambda _, v, w: w("<value><i8>%d</i8></value>" % v)

class PlayerControl(object):
    def __init__(self, host, port, playerID, ai_flag = False, ai_type = -1, name = 'Alice', stack = 4000):
        self.server = xmlrpc.client.ServerProxy('http://localhost:8000')
        self.daemon = True

        self._ai_flag = ai_flag
        self.playerID = playerID
        if ai_type == None:
            self._ai_type = ai_type
        if self._ai_flag:
            self._ai_type = ai_type
            if self._ai_type == 0:
                self.ai = HoldemAI(uuid.uuid4())
                print(self.ai.networkID)
        
        self._name = name
        self.host = host
        self.port = port
        self._stack = stack
        self._hand = []
        self.add_player()
    def get_ai_id(self):
        if self._ai_type == 0:
            return str(self.ai.networkID)
        else:
            return self._ai_type

    def save_ai_state(self):
        if self._ai_flag and self._ai_type == 0:
            print('AI type NEURAL NETWORK won (', self.get_ai_id(), ')')
            print(self.ai.networkID)
            #print(consec_wins)
            #self.writer.write([self.ai.networkID, consec_wins])
            self.ai.save()
        else:
            print('AI type ', self._ai_type, 'won')

    def delete_ai(self):
        if self._ai_type == 0:
            self.ai.delete()

    def new_ai(self, ai_id):
        if ai_id == 'unchanged':
            pass
        else:
            self.ai = HoldemAI(ai_id) # defaults to random network if ai_id not recognized

    def add_player(self):
        print('Player', self.playerID, 'joining game', self._ai_type)
        self.server.add_player(self.host, self.port, self.playerID, self._name, self._stack)

    def remove_player(self):
        self.server.remove_player(self.playerID)

    def rejoin(self):
        self.remove_player()
        self.reset_stack()
        self.add_player()

    def rejoin_new(self, ai_id):
        self.new_ai(ai_id)
        self.rejoin()

    def new_ai_type(self, ai_type):
        self._ai_type = ai_type

    def reset_stack(self):
        self._stack = 4000

    def print_table(self, table_state):
        print('Stacks:')
        players = table_state.get('players', None)
        for player in players:
            print(player[4], ': ', player[1], end='')
            if player[2] == True:
                print('(P)', end='')
            if player[3] == True:
                print('(Bet)', end='')
            if player[0] == table_state.get('button'):
                print('(Button)', end='')
            if players.index(player) == table_state.get('my_seat'):
                print('(me)', end='')
            print('')

        print('Community cards: ', end='')
        Card.print_pretty_cards(table_state.get('community', None))
        print('Pot size: ', table_state.get('pot', None))

        print('Pocket cards: ', end='')
        Card.print_pretty_cards(table_state.get('pocket_cards', None))
        print('To call: ', table_state.get('tocall', None))

    def update_localstate(self, table_state):
        self._stack = table_state.get('stack')
        self._hand = table_state.get('pocket')

    # cleanup
    def player_move(self, table_state):
        self.update_localstate(table_state)
        bigblind = table_state.get('bigblind')
        smallblind = table_state.get('smallblind')
        totalpot = table_state.get('pot')
        lastraise = table_state.get('lastraise')
        tocall = min(table_state.get('tocall', None),self._stack)
        minraise = table_state.get('minraise', None)
        hand = table_state.get('pocket_cards', None)
        players = table_state.get('players', None)
        myseat = table_state.get('my_seat')
        # print('minraise ', minraise)
        #move_tuple = ('Exception!',-1)
            
        # ask this human what their move is
        if not self._ai_flag:
            self.print_table(table_state)
            if tocall == 0:
                print('1) Raise')
                print('2) Check')
                try:
                    choice = int(input('Choose your option: '))
                except:
                    choice = 0
                if choice == 1:
                    choice2 = int(input('How much would you like to raise to? (min = {}, max = {})'.format(minraise,self._stack)))
                    while choice2 < minraise:
                        choice2 = int(input('(Invalid input) How much would you like to raise? (min = {}, max = {})'.format(minraise,self._stack)))
                    move_tuple = ('raise',choice2)
                elif choice == 2:
                  move_tuple = ('check', 0)
                else:
                    move_tuple = ('check', 0)
            else:
                print('1) Raise')
                print('2) Call')
                print('3) Fold')
                try:
                    choice = int(input('Choose your option: '))
                except:
                    choice = 0
                if choice == 1:
                    choice2 = int(input('How much would you like to raise to? (min = {}, max = {})'.format(minraise,self._stack)))
                    while choice2 < minraise:
                        choice2 = int(input('(Invalid input) How much would you like to raise to? (min = {}, max = {})'.format(minraise,self._stack)))
                    move_tuple = ('raise',choice2)
                elif choice == 2:
                    move_tuple = ('call', tocall)
                elif choice == 3:
                   move_tuple = ('fold', -1)
                else:
                    move_tuple = ('call', tocall)

        # feed table state to ai and get a response
        else:
            # neural network output
            if self._ai_type == 0:
                # neural network output
                move_tuple = self.ai.act(table_state)

            elif self._ai_type == 1:
                if tocall >0:
                    # 0 - Raise
                    # 1 - Call
                    # 2 - Fold
                    move_idx = np.random.randint(0,2)
                    if move_idx == 0:
                        try:
                            bet_size = np.random.randint(minraise, self._stack)
                            bet_size -= bet_size % bigblind
                        except:
                            bet_size = self._stack
                        if bet_size <= tocall:
                            move_tuple = ('call', tocall)
                        else:
                            move_tuple = ('raise', bet_size)
                    elif move_idx == 1:
                        move_tuple = ('call', tocall)
                    else:
                        move_tuple = ('fold', -1)
                else:
                    # 0 - Raise
                    # 1 - Check
                    move_idx = np.random.randint(0,1)
                    if move_idx == 0:
                        try:
                            bet_size = np.random.randint(minraise, self._stack)
                            bet_size -= bet_size % bigblind
                        except:
                            bet_size = self._stack
                        move_tuple = ('raise', bet_size)
                    else:
                        move_tuple = ('check',0)

            elif self._ai_type == 2:
                # check/call bot
                if tocall > 0:
                    move_tuple = ('call',tocall)
                else:
                    move_tuple = ('check', 0)

            # sklansky all-in tournament strategy
            elif self._ai_type == 3:
                score = 0
                ytp = 0
                limpers = 1
                total_blinds = (bigblind + smallblind)
                score = (self._stack/total_blinds)
                raw_values = []
                raw_suit = []
                GAI = True
                
                #if totalpot <= total_blinds:
                    #print('1 limper')
                    #limpers += 1
                
                for player in players:
                    if player[4] > myseat and player[2] == True:
                        ytp += 1
                    
                for n in range(len(hand)):
                    raw_values.append(Card.get_rank_int(hand[n]))
                    raw_suit.append(Card.get_suit_int(hand[n]))

                
                score *= ytp
                score *= limpers #improve this
                
                score = (int(score))
                score = abs(score)
  
                         
                raw_values.sort()
                #print(list(raw_values) + list(raw_suit))
                key=((range(0,19)), (range(20,39)), (range(40,59)), (range(60,79)), (range(80,99)), (range(100,149)), (range(150,199)), (range(200, 399)), (range(400, 999)))
                
                for k in key:
                    if score in k:
                        pointer = key.index(k)
                        
                if tocall > 0:
                    
                    if raw_values in ([12, 12], [11, 11]):
                        GAI = True
                    elif raw_values in [11, 12] and raw_suit[0] == raw_suit[1]: # add flush
                        GAI = True
                    elif score > 400 and raw_values in [12, 12]:
                        GAI = True
                    if score in range (200,399) and raw_values in ([12,12], [11,11]):
                        GAI = True
                    elif score in range (150,199) and raw_values in ([12,12], [11,11], [10,10],[11,12]):
                        GAI = Tr
                    elif score in range (100,149) and raw_values in ([12,12], [11,11], [10,10],[9,9],[8,8],[11,12],[10,12],[10,11]):
                        GAI = True
                    elif score in range (80,99):
                        if raw_values[0] == raw_values[1]:
                            GAI = True
                        elif raw_values in ([11,12], [10,12], [10,11]):
                            GAI = True
                        elif raw_suit[0] == raw_suit[1] and 12 in raw_values:
                            GAI = True
                        elif (raw_values[1] - 1) <= raw_values[0] and raw_suit[0] == raw_suit[1]: #refine
                            if raw_values[0] >= 2:
                                GAI = True
                                #print("straight poss above 4")
                            else:
                                GAI = False
                    elif score in range (60,79):
                        if raw_values[0] == raw_values[1]:
                            GAI = True
                        elif 12 in raw_values:
                            GAI = True
                        elif raw_values in [10,11]:
                            GAI = True
                        elif raw_suit[0] == raw_suit[1] and 11 in raw_values:
                            GAI = True
                        #add one-gap and no-gap suited connectors
                    elif score in range (40, 59):
                        if raw_values[0] == raw_values[1]:
                            GAI = True
                        elif 12 or 11 in raw_values:
                            GAI = True
                        elif raw_suit[0] == raw_suit[1] and 11 in raw_values:
                            GAI = True
                        #add gap too!
                    elif score in range (20, 39):
                        if raw_values[0] == raw_values[1]:
                            GAI = True
                        elif 12 or 11 in raw_values:
                            GAI = True
                        elif raw_suit[0] == raw_suit[1]:
                            GAI = True
                    elif score in range (0, 19):
                        GAI = True
                    else:
                        GAI = False
                else:
                    GAI = False
                                           
                if GAI == True:
                    print('GAI is true')
                    try:
                        bet_size = self._stack
                    except:
                        bet_size = self._stack
                    move_tuple = ('raise', bet_size)
                else:
                    #print('Folding')
                    move_tuple = ('fold',-1)
                

##Key Number = 400 or more: Move in with AA and fold everything else.
##Key Number = 200 to 400: Move in with AA and KK only.
##Key Number = 150 to 200: Move in with AA, KK, QQ and AK
##Key Number = 100 to 150: Move in with AA, KK, QQ, JJ, TT, AK, AQ and KQ
##Key Number = 80 to 100: Move in with any pair, AK, AQ, KQ, any suited Ace and
##any suited connector down to 5-4 suited.
##Key Number = 60 to 80: Move in with any pair, any ace, KQ, any suited king
##and all one-gap and no-gap suited connectors.
##Key Number = 40 to 60: Move in with everything above + any king.
##Key Number = 20 to 40: Move in with everything above + any 2 suited cards
##Key Number = <20: Move in with any 2-cards.
            
            else:
                if tocall >0:
                    # 0 - Raise
                    # 1 - Call
                    # 2 - Fold
                    move_idx = np.random.randint(0,2)
                    if move_idx == 0:
                        try:
                            bet_size = np.random.randint(minraise, self._stack)
                            bet_size -= bet_size % bigblind
                        except:
                            bet_size = self._stack
                        if bet_size <= tocall:
                            move_tuple = ('call', tocall)
                        else:
                            move_tuple = ('raise', bet_size)
                    elif move_idx == 1:
                        move_tuple = ('call', tocall)
                    else:
                        move_tuple = ('fold', -1)
                else:
                    # 0 - Raise
                    # 1 - Check
                    move_idx = np.random.randint(0,1)
                    if move_idx == 0:
                        try:
                            bet_size = np.random.randint(minraise, self._stack)
                            bet_size -= bet_size % bigblind
                        except:
                            bet_size = np.random.randint(minraise, self._stack)
                        move_tuple = ('raise', bet_size)
                    else:
                        move_tuple = ('check',0)

        return move_tuple

class PlayerControlProxy(object):
    def __init__(self,player):
        self._quit = False

        self._player = player
        self.server = SimpleXMLRPCServer((self._player.host, self._player.port), logRequests=False, allow_none=True)
        self.server.register_instance(self, allow_dotted_names=True)
        Thread(target = self.run).start()

    def run(self):
        while not self._quit:
            self.server.handle_request()

    def player_move(self, output_spec):
        return self._player.player_move(output_spec)

    def print_table(self, table_state):
        self._player.print_table(table_state)

    def join(self):
        self._player.add_player()

    def rejoin_new(self, ai_id = 'unchanged'):
        self._player.rejoin_new(ai_id)

    def rejoin(self, ai_type = 0):
        self._player.rejoin()

    def get_ai_id(self):
        return self._player.get_ai_id()

    def save_ai_state(self):
        self._player.save_ai_state()

    def delete_ai(self):
        self._player.delete_ai()

    def quit(self):
        self._player.server.remove_player(self._player.playerID)
        self._quit = True
