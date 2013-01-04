'''
December 26, 2012
Justin Thomsen

Version 2 of Web Blackjack. All functionalities except splitting now supported. Optimized for playing in Chrome.

Changes in version 2:
    - Insurance routing structure and functionality now complete

Future changes (anticipated version):
    - Splitting hands (version 3)
    - Code refactoring to hide lower-level structures from user, preventing direct access to the game state (version 4)

'''

from __future__ import division
from google.appengine.api import memcache
from modules.base import AppHandler
from modules.authentication import validate, make_secure_val
from main import Users, BlackjackGames
import string
from random import randint
import blackjack as bj

class NewBlackjack(AppHandler):
    
    '''
        - Validate the user (can't play unless logged in)
        - Create a new game state in the data store
        - BlackjackGames datastore allows users to save/continue games in progress
    '''
    def get(self):
        # validate user to allow game to begin
        user_id = validate(self.request.cookies.get('user_id'))
        
        if user_id:
            user = Users.get_by_id(int(user_id))
            
            # validate game_id to check for in progress, valid game state for user          
            game_id = validate(self.request.cookies.get('game_id'))
            
            # get chips and deck from memcache if possible else from db
            chips = memcache.get('%s_chips' % user_id)
            deck = memcache.get('%s_deck' % user_id)
            #print deck
            if not deck: deck = ['']
            if not chips: chips = user.chips
            
            message = 'Shuffling the deck!' if len(deck) < 20 else ''
            maximum = chips if chips < 500.0 else 500
            if chips < 5.0:
                chips += 500.0
                user.chips += 500.0
                user.chipresets += 1
                user.put()
                memcache.set('%s_chips' % user_id, chips, time=3600)
                message += '\nYou ran out of chips! You have been given 500 more!'  
                      
            if not game_id: # create game if user does not already have one in progress
                game = BlackjackGames(gameuser = user.username,
                                      gameuserid = int(user_id),
                                      playerhand = [''],
                                      playerhand2 = [''],
                                      playerhand3 = [''],
                                      playerhand4 = [''],
                                      dealerhand = [''],
                                      deck = [''],
                                      playerbet = 0,
                                      playerbet2 = 0,
                                      playerbet3 = 0,
                                      playerbet4 = 0)
                game = game.put()
                game_id = make_secure_val(str(game.id()))
                self.response.headers.add_header('Set-Cookie', 'game_id=%s; Path=/' % str(game_id))
                
            else:   # continue if in the middle of a game
                game = BlackjackGames.get_by_id(int(game_id))
                
            self.render('blackjack_newgame.html', username = user.username, chipcount = chips, 
                        message = message, maximum = maximum)
        
        # if can't validate user, render casino_front_out to prompt for signup/login
        else:
            user = None
            self.render('casino_front_out.html')
            
            
    '''
        - Determine if the user chose to play and validate user and gamestate
        - Create a new Blackjack game and deal out a new hand, update datastore
    '''
    def post(self):
        play = self.request.POST.get('play', None)
        end = self.request.POST.get('quit', None)
        bet = self.request.POST.get('quantity', None)
        
        # validate game state and user to protect against cheating
        user_id = validate(self.request.cookies.get('user_id'))
        game_id = validate(self.request.cookies.get('game_id'))
        chips = memcache.get('%s_chips' % user_id)
        if not chips: chips = user.chips
        
        if user_id and game_id:
            if play and (not bet or float(bet) > chips): # cannot continue without submitting a bet
                self.redirect('/newbj') 
                
            elif end: # delete the game from data store and local cookies if quitting
                BlackjackGames.get_by_id(int(game_id)).delete()
                self.response.headers.add_header('Set-Cookie', 'game_id= ; Path=/')
                self.redirect('/')
                
            elif play:
                # pull user and game from data store
                user = Users.get_by_id(int(user_id))
                game = BlackjackGames.get_by_id(int(game_id))
            
                g = bj.Game(chips)
                
                # new shuffled deck is created in g,
                # replace with current deck if current deck has >20 cards remaining
                deck = memcache.get('%s_deck' % user_id)
                if not deck: deck = game.deck
                if len(deck) > 20: 
                    g.table.deck.cards = [bj.Card(card[:1], card[1:], card) for card in game.deck]
                
                # deal hand and access data from hands  
                # ensure each hand is of correct length before continuing  
                g.new_hand()
                deck = [card.name for card in g.table.deck.cards[4:]]
                playerhand = [card.name for card in g.table.players[0].cards[0]]
                dealerhand = [card.name for card in g.table.dealer.cards[0]]
                try:
                    assert '' not in playerhand and '' not in dealerhand
                    assert len(playerhand) == 2 and len(dealerhand) == 2
                except AssertionError:
                    playerhand = [card for card in playerhand if card != '']
                    dealerhand = [card for card in dealerhand if card != '']
                    if len(playerhand) == 1:
                        g.hit_hand(0, 0)
                        deck = deck[1:]
                        playerhand += [g.table.players[0].cards[0][1].name]
                    if len(dealerhand) == 1:
                        g.hit_hand(0)
                        deck = deck[1:]
                        dealerhand += [g.table.dealer.cards[0][1].name]
                        
                           
                # subtract wagered chips out from user at the time of betting
                playerbet = int(bet)
                chips = user.chips - playerbet
            
                # update game and user in data store
                game.deck = deck
                game.playerhand = playerhand
                game.dealerhand = dealerhand
                game.playerbet = playerbet
                game.put()
                user.chips = chips
                user.put()
            
                # add game state to memcache
                memcache.set_multi({'_deck': deck,
                                    '_phand': playerhand,
                                    '_dhand': dealerhand,
                                    '_bet': playerbet,
                                    '_chips': chips},
                                    key_prefix="%s" % user_id, time=3600)
                
                
            
                # count up the value of each player's hand to determine which course the game follows
                ptotal = g.table.players[0].hand_sum[0]
                dtotal = g.table.dealer.hand_sum[0]
                
                # offer insurance to the player if the second dealer card is an Ace
                if str(dealerhand[1]) in ['AH', 'AS', 'AD', 'AC']:
                    self.redirect('/insurancebj')
                elif ptotal == 21 and dtotal == 21: # blackjack push, game ends
                    self.redirect('/resultsbj?p=21&d=21&result=push')
                elif ptotal == 21: # player blackjack, game ends
                    self.redirect('/resultsbj?p=21&d=%s&result=pblackjack' % dtotal)
                elif dtotal == 21: # dealer blackjack, game ends ### double check that it is working...
                    self.redirect('/resultsbj?p=%s&d=21&result=dblackjack' % ptotal)
                else: # no blackjacks, game continues
                    self.redirect('/playbj?h=1')
        
        # if game_id and user_id could not be validated, redirect to main page
        else: 
            self.redirect('/')
            
            
            
class InsuranceBlackjack(AppHandler):
    def get(self):
        # validate game state and user to protect against cheating
        user_id = validate(self.request.cookies.get('user_id'))
        game_id = validate(self.request.cookies.get('game_id'))
        
        if user_id and game_id:
            user = Users.get_by_id(int(user_id))
            game = BlackjackGames.get_by_id(int(game_id))
            
            # check memcache for the bet for this game, 
            # insurance costs lesser of .5 * wager or user's total chip count
            # attempt to retrieve hands, bet, chips from memcache
            values = memcache.get_multi(['_phand', '_dhand', '_bet', '_chips'], 
                                        key_prefix='%s' % user_id)
            playerhand = values['_phand'] if '_phand' in values else None
            dealerhand = values['_dhand'] if '_dhand' in values else None
            playerbet = values['_bet'] if '_bet' in values else None
            chips = values['_chips'] if '_chips' in values else None
            if not playerhand: playerhand = game.playerhand
            if not dealerhand: dealerhand = game.dealerhand
            if not playerbet: playerbet = game.playerbet
            if not chips: chips = user.chips
            
            ins = min(playerbet/2, chips)
            memcache.set('%s_ins' % user_id, ins, 3600)

            self.render('blackjack_insurance.html', username = user.username, 
                                                    d_cards = ['rbv', dealerhand[1]],
                                                    p_cards = playerhand,
                                                    ins = ins, chips = chips)
        
        # if game_id and user_id cannot be validated, render casino_front_out page
        else:
            user = None
            self.render('casino_front_out.html')


    def post(self):
        # validate game state and user to protect against cheating
        game_id = validate(self.request.cookies.get('game_id'))
        user_id = validate(self.request.cookies.get('user_id'))
        
        if user_id and game_id:
            # determine if user bought insurance
            buy = self.request.POST.get('buy', None)
            nobuy = self.request.POST.get('nobuy', None)
            user = Users.get_by_id(int(user_id))
            game = BlackjackGames.get_by_id(int(game_id))
            
            # get the bet and chips for this game and user
            values = memcache.get_multi(['_phand', '_dhand', '_chips', 
                                         '_ins'], key_prefix='%s' % user_id)
            playerhand = values['_phand'] if '_phand' in values else None
            dealerhand = values['_dhand'] if '_dhand' in values else None
            ins = values['_ins'] if '_ins' in values else None
            chips = values['_chips'] if '_chips' in values else None
            if not playerhand: playerhand = game.playerhand
            if not dealerhand: dealerhand = game.dealerhand
            if not chips: chips = user.chips
            if not ins: ins = min(game.playerbet/2, chips)
            
            if buy:                
                # decrease player chip count at time of insurance purchase
                user.chips -= ins
                chips -= ins
                memcache.set('%s_chips' % user_id, chips, 3600)
                user.put()
                
            # re-establish a game
            g = bj.Game(chips)
            
            # reassemble player hand in g
            g.table.players[0].cards[0] = [bj.Card(card[:1], card[1:], card) for card in playerhand]
            for card in g.table.players[0].cards[0]:
                if card.value == "A":
                    g.table.players[0].soft[0] += 1
                g.table.players[0].sum_card(0, card.value)
            
            # reassemble dealer hand in g    
            g.table.dealer.cards[0] = [bj.Card(card[:1], card[1:], card) for card in dealerhand]
            for card in g.table.dealer.cards[0]:
                if card.value == "A":
                    g.table.dealer.soft[0] += 1
                g.table.dealer.sum_card(0, card.value)
        
            # count up the value of each player's hand to determine which course the game follows
            dtotal = g.table.dealer.hand_sum[0]
            ptotal = g.table.players[0].hand_sum[0]
        
            #add cases for player blackjack!!!
            if dtotal == 21 and ptotal < 21 and buy: # dealer bj & player has ins
                self.redirect('/resultsbj?p=%s&d=21&result=dblackjack&ins=win' % ptotal)
            elif dtotal == 21 and ptotal < 21 and nobuy: # dealer bj but no ins
                self.redirect('/resultsbj?p=%s&d=21&result=dblackjack'% ptotal)
            elif dtotal == 21 and ptotal == 21 and buy:
                self.redirect('/resultsbj?p=21&d=21&result=push&ins=win')
            elif dtotal == 21 and ptotal == 21 and nobuy:
                self.redirect('/resultsbj?p=21&d=21&result=push')
            elif dtotal != 21 and ptotal < 21 and buy: # no dealer bj but has ins
                self.redirect('/loseins')
            elif dtotal != 21 and ptotal < 21 and nobuy: # no dealer bj & no ins
                self.redirect('/playbj?h=1')
            elif dtotal != 21 and ptotal == 21 and buy:
                self.redirect('/resultsbj?p=21&d=%s&result=pblackjack&ins=lose' % dtotal)
            elif dtotal != 21 and dtotal == 21 and nobuy:
                self.redirect('/resultsbj?p=21&d=%s&result=pblackjack' % dtotal)
        # if game_id and user_id could not be validated, redirect to main page
        else: 
            self.redirect('/')
        
class LoseInsurance(AppHandler):
    def get(self):
        # validate game state and user to protect against cheating
        user_id = validate(self.request.cookies.get('user_id'))
        game_id = validate(self.request.cookies.get('game_id'))
        
        if user_id and game_id:
            user = Users.get_by_id(int(user_id))
            game = BlackjackGames.get_by_id(int(game_id))
            
            # get bet from memcache if possible
            ins = memcache.get('%s_ins' % user_id)
            chips = memcache.get('%s_chips' % user_id)
            if not chips: chips = user.chips
            if not ins: ins = min(game.playerbet/2, chips)

            self.render('lose_insurance.html', ins = ins, chips = chips)
        
        # if game_id and user_id cannot be validated, render casino_front_out page
        else:
            user = None
            self.render('casino_front_out.html')


    # after accepting insurance loss message, continue playing game
    def post(self):
        self.redirect('/playbj?h=1')
        
#don't allow double/split for less right now
# pass which hand the player is currently playing as a query parameter*******
class PlayBlackjack(AppHandler):

    def get(self):
        user_id = validate(self.request.cookies.get('user_id'))
        game_id = validate(self.request.cookies.get('game_id'))
        
        # validate game state and user to protect against cheating
        if user_id and game_id:
            user = Users.get_by_id(int(user_id))
            game = BlackjackGames.get_by_id(int(game_id))
            
            current = self.request.get('h')
            # attempt to retrieve hands, bet, chips from memcache
            values = memcache.get_multi(['_phand', '_dhand', '_bet', '_chips'], 
                                        key_prefix='%s' % user_id)
            playerhand = values['_phand'] if '_phand' in values else None
            dealerhand = values['_dhand'] if '_dhand' in values else None
            playerbet = values['_bet'] if '_bet' in values else None
            chips = values['_chips'] if '_chips' in values else None
            if not playerhand: playerhand = game.playerhand
            if not dealerhand: dealerhand = game.dealerhand
            if not playerbet: playerbet = game.playerbet
            if not chips: chips = user.chips
            
            # doubling and splitting only enabled in legal circumstances
            double = 'disabled' 
            split = 'disabled'
            if len(game.playerhand) == 2 and chips >= playerbet:
                double = ''
                #if game.playerhand[0][:1] == game.playerhand[1][:1]:
                    #split = ''
                
            self.render('blackjack_table.html', username = user.username, 
                                                d_cards = ['rbv', dealerhand[1]], 
                                                p_cards = playerhand,
                                                double = double,
                                                split = split)
        
        # if game_id and user_id cannot be validated, render casino_front_out page
        else:
            user = None
            self.render('casino_front_out.html')
    
    
    def post(self):
        game_id = validate(self.request.cookies.get('game_id'))
        user_id = validate(self.request.cookies.get('user_id'))
        
        # validate game state and user to protect against cheating
        if game_id:
            user = Users.get_by_id(int(user_id))
            game = BlackjackGames.get_by_id(int(game_id))
            
            # attempt to retrieve hands, bet, chips from memcache or pull from db
            values = memcache.get_multi(['_phand', '_dhand', '_bet', '_chips', '_deck'], 
                                        key_prefix='%s' % user_id)
            playerhand = values['_phand'] if '_phand' in values else None
            dealerhand = values['_dhand'] if '_dhand' in values else None
            playerbet = values['_bet'] if '_bet' in values else None
            chips = values['_chips'] if '_chips' in values else None
            deck = values['_deck'] if '_deck' in values else None
            if not playerhand: playerhand = game.playerhand
            if not dealerhand: dealerhand = game.dealerhand
            if not playerbet: playerbet = game.playerbet
            if not deck: deck = game.deck
            if not chips: chips = user.chips
            
            # re-establish a game
            g = bj.Game(chips)
            
            # reassemble player hand in g
            g.table.players[0].cards[0] = [bj.Card(card[:1], card[1:], card) for card in playerhand]
            for card in g.table.players[0].cards[0]:
                if card.value == "A":
                    g.table.players[0].soft[0] += 1
                g.table.players[0].sum_card(0, card.value)
            
            # reassemble dealer hand in g    
            g.table.dealer.cards[0] = [bj.Card(card[:1], card[1:], card) for card in dealerhand]
            for card in g.table.dealer.cards[0]:
                if card.value == "A":
                    g.table.dealer.soft[0] += 1
                g.table.dealer.sum_card(0, card.value)
                
            # reassemble deck in g     
            g.table.deck.cards = [bj.Card(card[:1], card[1:], card) for card in deck]
            
            # retrieve player's selected action
            hit = self.request.POST.get('hit', None)
            stay = self.request.POST.get('stay', None)
            double = self.request.POST.get('double', None)
            split = self.request.POST.get('split', None)
            current = self.request.get('h')
            
            # procedure for hitting
            if hit:
                # add next card to index-0 hand in index-0 player (player 1, hand 1)
                g.hit(0, 0)
                
                # update db and memcache
                deck = [card.name for card in g.table.deck.cards[1:]]
                playerhand = [card.name for card in g.table.players[0].cards[0]]
                game.deck = deck
                game.playerhand = playerhand
                game.put()
                memcache.set('%s_deck' % user_id, deck, 300)
                memcache.set('%s_phand' % user_id, playerhand, 300)
                
                # if player has 21 or under, can continue playing else, immediately end game
                ptotal = g.table.players[0].hand_sum[0]
                if ptotal <= 21:
                    self.redirect('/playbj?h=1')
                if ptotal > 21:
                    dtotal = g.table.dealer.hand_sum[0]
                    self.redirect('/resultsbj?p=%s&d=%s&result=loss' % (ptotal, dtotal))
                    
            # procedure for staying and doubling
            elif stay or double:
                count = 0 # number of cards dealt out during procedure
                
                # hit 1 on double, then stay automatically
                if double != None:
                    g.hit(0, 0)
                    playerhand = [card.name for card in g.table.players[0].cards[0]] 
                    
                    chips -= playerbet                
                    playerbet *= 2 
                    game.playerbet = playerbet # will be .put() into db after dealer's turn
                    game.playerhand = playerhand
                    memcache.set_multi({'_bet': playerbet,
                                        '_phand': playerhand,
                                        '_chips': chips},
                                        key_prefix='%s' % user_id, time=3600)
                    
                    user.chips = chips 
                    user.put()
                    count += 1  
                
                # dealer hits on soft 17 or lower                    
                dtotal = g.table.dealer.hand_sum[0]
                while (dtotal == 17 and g.table.dealer.soft[0] >= 1) or dtotal < 17:
                    # with only one parameter, hits to specified-index hand in dealer
                    g.hit(0)
                    count += 1
                    dtotal = g.table.dealer.hand_sum[0]
                
                deck = [card.name for card in g.table.deck.cards[count:]]
                dealerhand = [card.name for card in g.table.dealer.cards[0]]
                
                # update deck and dealerhand in memcache & db
                memcache.set('%s_deck' % user_id, deck, time=3600)
                memcache.set('%s_dhand' % user_id, dealerhand, time=3600)
                game.deck = deck
                game.dealerhand = dealerhand
                game.put()
                
                # evaluate results and redirect to game results screen
                ptotal = g.table.players[0].hand_sum[0]
                if (ptotal > dtotal and ptotal <= 21) or dtotal > 21:
                    self.redirect('/resultsbj?p=%s&d=%s&result=win' % (ptotal, dtotal))
                elif (ptotal < dtotal and dtotal <= 21) or ptotal > 21:
                    self.redirect('/resultsbj?p=%s&d=%s&result=loss' % (ptotal, dtotal))
                elif ptotal == dtotal:
                    self.redirect('/resultsbj?p=%s&d=%s&result=push' % (ptotal, dtotal))
            
            # placeholder procedure for splitting. not currently supported
            elif split:
                pass
            
        # if game_id and user_id could not be validated, redirect to main page
        else: 
            self.redirect('/')
        
class ResultsBlackjack(AppHandler):
    
    def get(self):
        user_id = validate(self.request.cookies.get('user_id'))
        game_id = validate(self.request.cookies.get('game_id'))
        
        # validate game state and user to protect against cheating
        if user_id and game_id:
            user = Users.get_by_id(int(user_id))
            game = BlackjackGames.get_by_id(int(game_id))
            
            # attempt to retrieve hands, bet, chips from memcache or pull from db
            values = memcache.get_multi(['_phand', '_dhand', '_bet', '_chips'], 
                                        key_prefix='%s' % user_id)
            playerhand = values['_phand'] if '_phand' in values else None
            dealerhand = values['_dhand'] if '_dhand' in values else None
            playerbet = values['_bet'] if '_bet' in values else None
            chips = values['_chips'] if '_chips' in values else None
            if not playerhand: playerhand = game.playerhand
            if not dealerhand: dealerhand = game.dealerhand
            if not playerbet: playerbet = game.playerbet
            if not chips: chips = user.chips
            
            # update user's stats and chip count based on result, generate results message
            message = None
            
            if self.request.get('result') == 'win':
                chips += playerbet * 2 # 1:1 payout + initial wager returned
                memcache.set('%s_chips' % user_id, chips, time=3600)
                
                user.chips = chips 
                user.bjwins += 1
                user.bjearnings += playerbet
                
                message = "You have %s and the Dealer has %s. You win!" % (self.request.get('p'), self.request.get('d'))
                chipcount = "You win your wager and gain %s chips. You now have %s chips!" % (playerbet, chips)
             
            
            elif self.request.get('result') == 'pblackjack':
                payout = playerbet * 1.5
                chips += playerbet + payout # 3:2 payout + initial wager returned
                
                memcache.set('%s_chips' % user_id, chips, time=3600)
                
                user.chips = chips
                user.bjwins += 1
                user.bjearnings += payout
                
                message = "You have a blackjack! You win!"
                
                # chips were already adjusted during insurance, so nothing is done except notification of loss
                if self.request.get('ins') == 'lose':
                    ins = memcache.get('%s_ins' % user_id)
                    if not ins: ins = game.playerbet/2
                    message = "You have a blackjack!\n You lose your insurance wager of %s chips." % ins
                    
                chipcount = "You win your wager and gain %s chips. You now have %s chips!" % (payout, chips)
              
            # do not adjust chips for losses since wager was subtracted at beginning of hand
            elif self.request.get('result') == 'loss': 
                user.bjlosses += 1
                user.bjearnings -= playerbet
                
                message = "You have %s and the Dealer has %s. You lose!" % (self.request.get('p'), self.request.get('d'))
                chipcount = "You lose your wager of %s chips. You have %s remaining." % (playerbet, chips)
            
            # do not adjust chips for dealer bj since wager was subtracted at beginning of hand
            elif self.request.get('result') == 'dblackjack':
                message = "The dealer has a blackjack! You lose!"
                
                # if insurance was purchased, pays 2:1 at 50% of original wager, so return original wager
                if self.request.get('ins') == 'win':
                    chips += playerbet
                    user.chips = chips
                    memcache.set('%s_chips' % user_id, chips, time=3600)
                    message = "The dealer has a blackjack! You win your insurance wager and gain %s chips." % (playerbet)
                
                user.bjlosses += 1
                user.bjearnings -= playerbet
                chipcount = "You lose your wager of %s chips. You have %s remaining." % (playerbet, chips)
            
            # do not adjust any stats for push, refund original wager
            elif self.request.get('result') == 'push':
                chips += playerbet
                memcache.set('%s_chips' % user_id, chips, time=3600)
                user.chips = chips
                
                message = "You have %s and the Dealer has %s. You push!" % (self.request.get('p'), self.request.get('d'))
                
                # if insurance was purchased, pays 2:1 at 50% of original wager, so return original wager
                if self.request.get('ins') == 'win':
                    chips += playerbet
                    user.chips = chips
                    memcache.set('%s_chips' % user_id, chips, time=3600)
                    message = "You push with the dealer. You win your insurance wager and gain %s chips." % (playerbet)
                
                chipcount = "Your wager of %s chips has been returned. You have %s chips." % (playerbet, chips)
            
            user.bjgames += 1
            user.put()
            # render results page
            self.render('blackjack_final.html', username = user.username, 
                                                d_cards = dealerhand, 
                                                p_cards = playerhand,
                                                message = message,
                                                chipcount = chipcount)
        
        # if game_id and user_id could not be validated, redirect to main page
        else: 
            self.redirect('/')
    
    # redirect to new game screen after viewing results
    def post(self):
        self.redirect('/newbj')