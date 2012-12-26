'''
Created on Oct 4, 2012
Last updated 12/26/12
blackjack.py - web-blackjack version

Terminal window, object-oriented version of blackjack. 

Supports all aspects of game against dealer playing by house rules:
    - Player must stand on 21, may hit unlimited times while totalling less than 21
    - Dealer hits on soft 17, stands on anything higher
    - Dealer does not play if player busts all hands
    - Player may split equal cards in hand to yield up to 4 hands
    - Player may double on any two initial cards
    - Doubling and splitting "for less" permitted
    - Doubling receives one card only and the hand then terminates
    - Double after splitting permitted
    - Unlimited hitting on split aces
    - All chip bets must be integers
    - Blackjack pays 3:2
    - Insurance pays 2:1
    - Player with blackjack cannot take "even money" against dealer showing an Ace

Version notes:
    - Although currently only permitting one player, the data structures are set up so that the game could
        be easily modified to permit multiple players
    - Double deck blackjack by default with 500 chips to start. Could easily be set up to player preferences
        by asking player to define these prior to game beginning.


@author: Justin Thomsen
'''
import string
from random import randint

class Card(object):
    '''
        - Each card has a suit (HCDS) and value (23456789TJQKA)
    '''
    def __init__(self, value, suit, name):
        self.suit = suit
        self.value = value
        self.name = name

class Deck(object):
    '''
        - The game's deck holds a specified number of standard 52-card
               decks
        - Generator index starts at the 0th card in the deck
        - Generator triggers reshuffle 75% through the deck
        - Variable need_to_shuffle acts as the marker in the blackjack shoe
            to mark reshuffle point
        - names dictionary maps values and suits to their spelled out
            titles for the sake of readability in printing to console
        - NB (modified 12/23/12 specifically for the web-blackjack version): 
            Deck does not include AD. AD.png will not render in game due to corrupted file
            replaced with extra AS. Suit is irrelevant to blackjack, so this is merely a cosmetic
            alteration put in place until an acceptable image file is obtained.
    '''
    
    def __init__(self, num_decks):        
        self.decks = num_decks
        self.cards = [Card(v, s, v+s) for s in 'HCDS' for v in '23456789TJQK'
                      for _ in range(self.decks)] + [Card(v, s, v+s) for s in 'HCSS' for v in 'A' 
                                                     for _ in range(self.decks)]
        self.shuffle()
        self.genindex = 0
        self.need_to_shuffle = False
        self.names = {"2": "2", "3": "3", "4": "4", "5": "5", "6": "6", 
                      "7": "7", "8": "8", "9": "9", "T": "Ten", "J": "Jack",
                      "Q": "Queen", "K": "King", "A": "Ace", "H": "Hearts", 
                      "C": "Clubs", "D": "Diamonds", "S": "Spades"}

    # Knuth shuffle
    def shuffle(self):
        index = 0
        for card in self.cards:
            rep_index = randint(0,self.decks*52 - 1)
            temp = self.cards[rep_index]
            self.cards[rep_index] = card
            self.cards[index] = temp
            index += 1
        self.genindex = 0
        self.need_to_shuffle = False
        #print "SHUFFLED THE DECK!"
    
    # use generator to deal
    def deal_generator(self):
        for c in self.cards:
            yield c
            self.genindex += 1
            if self.genindex >= .75 * 52 * self.decks:
                self.need_to_shuffle = True

class Hand(object):
    '''
        - Each hand is a list of card lists. Storing as a list allows for split
            hands and keeping the hands in order.
        - Variable hand_sum keeps track of the total sum of each card list in
            the player's complete hand. Used for evaluating hand.
        - Variable hand_length keeps track of the length of each card list in
            the player's complete hand. Used to permit doubling and splitting.
        - Variable soft keeps track of the number of soft Aces currently held
            in each card list in the player's complete hand. Soft aces count
            count as 11 in the hand_sum.
        - Variable hand_count keeps track of how many card lists there are.
            Used to prevent player from splitting into more than 4 hands.
    '''
    
    def __init__(self):
        self.cards = [[]]
        self.hand_sum = [0]
        self.hand_length = [0]
        self.soft = [0]
        self.hand_count = 1
    
    # adds card to total sum of hand, hand over 21 w/ soft ace subtracts 10
    def sum_card(self, hand_number, value):
        if value.isdigit(): self.hand_sum[hand_number] += int(value)
        elif value != "A": self.hand_sum[hand_number] += 10
        elif value == "A":
            self.hand_sum[hand_number] += 11
        if self.hand_sum[hand_number] > 21 and self.soft[hand_number] >= 1:
            self.hand_sum[hand_number] -= 10
            self.soft[hand_number] -= 1
            
    # only used in splitting, leaving only 1 of two equal-value cards
    def subtract_card(self, hand_number, value):
        if value.isdigit(): self.hand_sum[hand_number] = int(value)
        elif value != "A": self.hand_sum[hand_number] = 10
        elif value == "A":
            self.hand_sum[hand_number] = 11
            self.soft[hand_number] = 1
    
    # reset all variables to original values
    def reset(self):
        self.cards = [[]]
        self.hand_sum = [0]
        self.hand_length = [0]
        self.soft = [0]
        self.hand_count = 1

class Player(Hand):
    '''
        - Player inherits from Hand
        - Variable chip_count tracks how many chips a player has available
        - Variable bet initialized as a list of bets corresponding to each hand
        - Variable insurance does not need a list because insurance plays only
            before standard game procedure and before hands can split
    '''
    def __init__(self, chip_count):
        Hand.__init__(self)
        self.chip_count = chip_count
        self.bet = [0]
        self.insurance = 0
        self.split = False

    # subtract wager in advance to prevent doubling with nonexistent chips
    def make_wager(self, wager, hand_num):
        self.chip_count -= wager
        self.bet[hand_num] += wager
    
    # get wager back plus 1:1 standard payout
    def win_hand(self, hand_num):
        self.chip_count += 2 * self.bet[hand_num]
        self.bet[hand_num] = 0
    
    # reset wager to 0, chips unchanged since chips were removed at wager time
    def lose_hand(self, hand_num): 
        self.bet[hand_num] = 0
    
    # give wager back
    def push_hand(self, hand_num):
        self.chip_count += self.bet[hand_num]
        self.bet[hand_num] = 0
    
    # get original wager back plus 3:2 payout on blackjack
    def win_blackjack(self):
        self.chip_count += 2.5 * self.bet[0]
        self.bet[0] = 0
    
    # side wager on insurance, functions like make_wager
    def make_insurance_wager(self, wager):
        self.chip_count -= wager
        self.insurance = wager
    
    # pay back insurance plus 1:1 payout:
    def win_insurance(self):
        self.chip_count += 2 * self.insurance
        self.insurance = 0
    
    # reset wager to 0, functions like lose_hand
    def lose_insurance(self):
        self.insurance = 0
    
    # reset player variables at end of hand
    def reset_player(self):
        self.reset()
        self.bet = [0]
        self.insurance = 0
        self.split = False
    
class Dealer(Hand):
    '''
        - Inherits from Hand, no special variables, considered a separate
            class purely for readability's sake in code
    '''
    def __init__(self):
        Hand.__init__(self)
    
class Table(object):
    '''
        - Initializes the dealer, all of the players, and the deck, as well
            as the deal generator
        - Table runs the basic "behind the scenes" operations for in-game
            actions: "hit_hand", "split_hand", and "evaluate_winner"
    '''
    def __init__(self, num_players, chips):
        self.dealer = Dealer()
        self.players = [Player(chips) for _ in range(num_players)]
        self.deck = Deck(2)
        self.deal = self.deck.deal_generator()
    
    # add a new card to the specified player's specified hand, or dealer
    def hit_hand(self, hand_num = 0, player_num = None):
        c = None
        try:
            c = self.deal.next()
        except StopIteration:
            self.deck = Deck(2)
            self.deal = self.deck.deal_generator()
            c = self.deal.next()
        if player_num != None:
            if c.value == "A":
                self.players[player_num].soft[hand_num] += 1
            self.players[player_num].cards[hand_num].append(c)
            self.players[player_num].sum_card(hand_num, c.value)
            self.players[player_num].hand_length[hand_num] += 1
        else:
            if c.value == "A":
                self.dealer.soft[hand_num] += 1
            self.dealer.cards[hand_num].append(c)
            self.dealer.sum_card(hand_num, c.value)
            self.dealer.hand_length[0] += 1
        return c.value
    
    #pop a card out of the specified hand and create another hand for the player
    def split_hand(self, hand_num, player_num):
        sp_card = self.players[player_num].cards[hand_num].pop()
        self.players[player_num].cards.append([sp_card])
        self.players[player_num].hand_sum.append(0)
        self.players[player_num].sum_card(self.players[player_num].hand_count, sp_card.value)
        self.players[player_num].hand_length[hand_num] = 1
        self.players[player_num].hand_length.append(1)
        self.players[player_num].bet.append(0)
        self.players[player_num].make_wager(self.players[player_num].bet[hand_num], (hand_num + 1))
        self.players[player_num].subtract_card(hand_num, sp_card.value)
        self.players[player_num].hand_count += 1
        self.players[player_num].split = True
        
        if sp_card.value == "A":
            self.players[player_num].soft.append(1)
            self.players[player_num].soft[hand_num] = 1
        else:
            self.players[player_num].soft.append(0)
        return self.hit_hand(hand_num, player_num)
    
    # check to see if the dealer is showing an ace
    def check_dealer_ace(self):
        return self.dealer.cards[0][1].value == "A"
    
    # determine winner between specified player's specified hand and dealer
    # push takes absolute precedence, followed by blackjacks, then comparisons
    def evaluate_winner(self, hand_num, player_num):
        p_hand = self.players[player_num].hand_sum[hand_num]
        p_hand_len = self.players[player_num].hand_length[hand_num]
        p_split = self.players[player_num].split
        d_hand = self.dealer.hand_sum[0]
        d_hand_len = self.dealer.hand_length[0]
        if d_hand_len == 2 and d_hand == 21 and p_hand != d_hand:
            self.players[player_num].lose_hand(hand_num)
            return "DEALER HAS A BLACKJACK!"
        elif p_hand_len == 2 and p_hand == 21 and not p_split and p_hand != d_hand: 
            self.players[player_num].win_blackjack()
            return "PLAYER #%s HAS A BLACKJACK!" % (player_num + 1)
        elif p_hand > 21 or (p_hand < d_hand and d_hand <= 21):
            self.players[player_num].lose_hand(hand_num)
            return "PLAYER #%s LOSES!" % (player_num + 1)
        elif d_hand > 21 or (p_hand > d_hand and p_hand <= 21):
            self.players[player_num].win_hand(hand_num)
            return "PLAYER #%s WINS!" % (player_num + 1)
        elif p_hand == d_hand:
            self.players[player_num].push_hand(hand_num)
            return "PLAYER #%s PUSHES WITH THE DEALER." % str(player_num + 1)
    
    # reset everything for the next hand
    def reset_hands(self):
        for player in self.players:
            player.reset_player()
        self.dealer.reset()

            
class Game(object):
    '''
        - Game class contains all of the "visible" work on a real casino table
        - Initializes the table
        - Variable num_of_players used in main function to loop over actions
            for all of the players at the table
        - Variable dealer_will_hit used to determine if dealer will draw any
            cards. Dealer only hits if there is at least one non-busted hand
        - Variables minimum and maximum store min and max bets
        
    '''
    def __init__(self, chips):
        self.table = Table(1, chips)
        self.num_of_players = 1
        self.dealer_will_hit = False
        self.minimum = 5
        self.maximum = 500
    
    # deal from generator, add to card list, sum the card value at time of deal
    def new_hand(self):
        if self.table.deck.need_to_shuffle:
            self.table.deck.shuffle()
            self.table.deal = self.table.deck.deal_generator()
        for _ in range(2):
            self.table.hit_hand(0)
            p_count = 0
            for _ in self.table.players:
                self.table.hit_hand(0, p_count)
                p_count += 1
    
    # current player hit
    def hit(self, hand_num = 0, player_num = None):
        return self.table.hit_hand(hand_num, player_num)
    
    # current player double down, player can double for less
    def double(self, wager, player_num, hand_num):
        chips = self.table.players[player_num].chip_count
        max_double = wager if wager < chips else chips
        double_wager = raw_input("Enter your double down wager."
                                 " You may bet up to %s chips.\n" % max_double)
        while (not double_wager.isdigit() 
                or int(double_wager) < 0
                or int(double_wager) > max_double):
            double_wager = raw_input("\nThat wager is invalid. \n"
                                     "You may bet up to %s chips.\n" % max_double)
        self.table.players[player_num].make_wager(int(double_wager), hand_num)
        print "\nYour wager is now %s chips.\n" % self.table.players[player_num].bet[hand_num]
        return self.table.hit_hand(hand_num, player_num)
    
    # offer insurance
    def offer_insurance(self, player_num):
        self.report_hands()
        buy = " "
        while string.upper(buy) not in "YN" or buy == "":
            buy = raw_input("The dealer is showing an Ace. Would you like to "
                            "buy insurance, Player #%s? Y/N \n" 
                            % (player_num + 1))
        if string.upper(buy) == "N": return
        else:
            wager = self.table.players[player_num].bet[0]
            chips = self.table.players[player_num].chip_count
            max_ins = wager if wager < chips else chips
            ins_wager = raw_input("Enter your insurance wager."
                                 " You may bet up to %s chips.\n" % max_ins)
            while (not ins_wager.isdigit() 
                   or int(ins_wager) < 0
                   or int(ins_wager) > max_ins):
                ins_wager = raw_input("\nThat wager is invalid. \n"
                                     "You may bet up to %s chips.\n" % max_ins)
            self.table.players[player_num].make_insurance_wager(int(ins_wager))
            return player_num
    
    # checks the dealer for blackjack and handles insurance wagers
    def check_dealer_blackjack(self, insurance_buyers):
        if self.table.dealer.hand_sum[0] == 21:
            if insurance_buyers:
                for player_num in insurance_buyers:
                    print ("The dealer has a blackjack! Player "
                           "#%s wins the insurance wager.\n" % (player_num + 1))
                    self.table.players[player_num].win_insurance()
                    print ("Total chips: %s" % self.table.players[player_num].chip_count)
                    raw_input("Press Enter to continue.")
            return True
        else:
            if insurance_buyers:
                for player_num in insurance_buyers:
                    print ("The dealer does not have a blackjack! Player "
                           "#%s loses the insurance wager.\n" % (player_num + 1))
                    self.table.players[player_num].lose_insurance()
                    print ("Total chips: %s" % self.table.players[player_num].chip_count)
                    raw_input("Press Enter to continue.")
            return False
            
                
        
    
    def check_dealer_ace(self):
        return self.table.dealer.cards[0][1].value == 'A'
    
    # current player splits
    def split(self, hand_num, player_num):
        return self.table.split_hand(hand_num, player_num)
    
    # current player places a bet
    def bets(self, player_num):
        wager = raw_input(("\nPlease enter a wager.\n"
                          "The table minimum is %s and the maximum is %s. \n"
                          "You have %s chips available. \n" 
                          % (self.minimum, self.maximum, self.table.players[player_num].chip_count)))
        while (not wager.isdigit() 
                    or int(wager) < self.minimum 
                    or int(wager) > self.maximum
                    or int(wager) > self.table.players[player_num].chip_count):
            wager = raw_input(("\nThat wager is invalid. \n"
                              "Please enter a wager between 5 and 500. \n"
                              "You have %s chips available. \n" 
                              % self.table.players[player_num].chip_count))
        self.table.players[player_num].make_wager(int(wager), 0)
        print "\nYou have wagered %s chips." % wager
    
    # main sequence for a player's turn
    def players_turn(self, player_num):
        
        # updates the value of a particular hand
        def update_sum(player_num, hand_num):
            return self.table.players[player_num].hand_sum[hand_num]
        
        # player chooses an action
        def player_action(player_num, hand_num, current_sum):
            val = None
            act = None
            if self.table.players[player_num].hand_length[hand_num] == 2:
                c1 = self.table.players[player_num].cards[hand_num][0]
                c2 = self.table.players[player_num].cards[hand_num][1]
                print "Hand #%s: " % (hand_num + 1)
                if (((c1.value == c2.value) or 
                     (c1.value in "TJQK" and c2.value in "TJQK")) and
                    (self.table.players[player_num].hand_count < 4)):
                    while (act != "HIT" and act != "STAY" and act != "DOUBLE"
                           and act != "SPLIT"):
                        act = string.upper(raw_input("What would you like to do? "
                                                     "HIT/STAY/DOUBLE/SPLIT\n"))
                else:
                    while act != "HIT" and act != "STAY" and act != "DOUBLE":
                        act = string.upper(raw_input("What would you like to do? "
                                                     "HIT/STAY/DOUBLE\n"))
            else:
                while act != "HIT" and act != "STAY":
                    act = string.upper(raw_input("What would you like to do? "
                                                 "HIT/STAY\n"))
            if act == "HIT":
                val = self.hit(hand_num, player_num)
                val = self.table.deck.names[val]
                return val
            elif act == "STAY":
                self.dealer_will_hit = True
                return False
            elif act == "DOUBLE":
                val = self.double(self.table.players[player_num].bet[hand_num],
                                  player_num, hand_num)
                val = self.table.deck.names[val]
                print ("\nYou received a %s. Hand total: %s." 
                       % (val, update_sum(player_num, hand_num)))
                if self.table.players[player_num].hand_sum[hand_num] <= 21:
                    self.dealer_will_hit = True
                return False
            elif act == "SPLIT":
                val = self.split(hand_num, player_num)
                val = self.table.deck.names[val]
                return val
        
        # report the results of player's action
        def summary(value, hand_num, current_sum):
            if current_sum > 21:
                print "\nYou received a %s on Hand #%s. Hand total: %s. You busted." % (value, hand_num + 1, current_sum)
                raw_input("Press Enter to continue.")
                return False
            elif current_sum == 21:
                print "\nYou received a %s on Hand #%s. Hand total: 21. Staying." % (value, hand_num + 1)
                self.dealer_will_hit = True
                raw_input("Press Enter to continue.")
                return False
            else:
                print "\nYou received a %s on Hand #%s. Hand total: %s." % (value, hand_num + 1, current_sum)
                raw_input("Press Enter to continue.")
                return True
        
        # loop over every hand the player has
        # number of hands can grow during the loop b/c data is stored as
        # list of lists rather than dictionary and split hands are added
        # to the list at a point after current hand
        # False returned from player_action or summary causes end of turn
        hand_num = 0
        for hand in self.table.players[player_num].cards:
            current_sum = update_sum(player_num, hand_num)
            if len(hand) == 1:
                print "\nFilling your next hand."
                val = self.hit(hand_num, player_num)
                current_sum = update_sum(player_num, hand_num)
                print ("You received a %s on Hand %s. Hand total: %s." % 
                       (val, hand_num + 1, current_sum))
                if current_sum == 21:
                    raw_input("Staying with 21. Press any key to continue.\n")
                else:
                    raw_input("Press any key to continue.\n")
            if current_sum == 21:
                self.dealer_will_hit = False
                hand_num += 1
                continue
            while True:
                self.report_hands()      
                value = player_action(player_num, hand_num, current_sum)
                if not value: break
                current_sum = update_sum(player_num, hand_num)
                if not summary(value, hand_num, current_sum): break
            hand_num += 1
            
    # sequence for dealer's turn, hits on soft 17
    def dealers_turn(self):
        if self.dealer_will_hit == True:
            while True:   
                dealer_sum = self.table.dealer.hand_sum[0]
                if (dealer_sum < 17 or (dealer_sum == 17 and self.table.dealer.soft[0] >= 1)):
                    self.hit(0)
                else:
                    break  
    
    # print out each hand in play, along with the wagers and totals of each
    # when play is not finished, the dealer's first card is not revealed
    def report_hands(self, final = False):
        card_number = 0
        print "\n....DEALER CARDS...."
        for card in self.table.dealer.cards[0]:
            if not final and card_number == 0: 
                print "-Hidden-"
                card_number += 1
            else: print self.table.deck.names[card.value], "of", self.table.deck.names[card.suit]
            
        if not final:
            dealer_total = self.table.dealer.cards[0][1].value
            if dealer_total == "A": dealer_total = 11
            elif dealer_total in "TJQK": dealer_total = 10
        else: dealer_total = self.table.dealer.hand_sum[0]
        
        print "Total: %s\n\n" % dealer_total
        
        player_count = 0
        for player in self.table.players:
            print "....PLAYER #%s's CARDS....\n" % (player_count + 1)
            hand_count = 0
            for hand in player.cards:
                print "----Hand #%s----" % (hand_count + 1)
                for card in hand:
                    print self.table.deck.names[card.value], "of", self.table.deck.names[card.suit]
                print "Total: %s" % player.hand_sum[hand_count]
                print "Wager: %s\n" % player.bet[hand_count]
                if final:
                    print self.table.evaluate_winner(hand_count, player_count)
                hand_count += 1
            player_count += 1

# main Blackjack function for program        
def __main__():
    g = Game(500)
    
    while True:
        # find out if player can/wants to play a round
        if g.table.players[0].chip_count <= g.minimum:
            print "You do not have enough chips to play."
            break
        play = " "
        while string.upper(play) not in "YN" or play == "":
            play = raw_input("Would you like to play? Y/N \n")
        if string.upper(play) == "N":
            break
                
        # push prior data out of interpreter console to simulate discarded cards
        print ("\n" * 35)
        
        # get bets for all players at the table
        for player_num in range(g.num_of_players):
            g.bets(player_num)        
        g.new_hand()
        
        # add insurance buyers if the dealer has an ace showing
        insurance_buyers = []
        if g.check_dealer_ace():
            for player_num in range(g.num_of_players):
                result = g.offer_insurance(player_num)
                if result != None: insurance_buyers.append(result)
        
        dealer_blackjack = g.check_dealer_blackjack(insurance_buyers)
        
        # if no dealer blackjack, each player takes a turn followed by dealer
        if not dealer_blackjack:
            for player_num in range(g.num_of_players):
                g.players_turn(player_num)
            g.dealers_turn()
        
        # report round results + reset
        g.report_hands(final = True)
        g.table.reset_hands()
        g.dealer_will_hit = False
    
    # return chip count of player
    return g.table.players[0].chip_count
