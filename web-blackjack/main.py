#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
from webapp2 import WSGIApplication, Route
from google.appengine.ext import db

# Set useful fields
root_dir = os.path.dirname(__file__)
template_dir = os.path.join(root_dir, 'templates')

class Users(db.Model):
    username = db.StringProperty(required = True)
    phash = db.StringProperty(required = True)
    email = db.StringProperty(required = False)
    chips = db.FloatProperty(required = True)
    chipresets = db.IntegerProperty(required = True)
    bjwins = db.IntegerProperty(required = True)
    bjlosses = db.IntegerProperty(required = True)
    bjgames = db.IntegerProperty(required = True)
    bjearnings = db.FloatProperty(required = True)

class BlackjackGames(db.Model):
    gameuser = db.StringProperty(required = True)
    gameuserid = db.IntegerProperty(required = True)
    playerhand = db.StringListProperty(required = True)
    playerhand2 = db.StringListProperty(required = True)
    playerhand3 = db.StringListProperty(required = True)
    playerhand4 = db.StringListProperty(required = True)
    playerbet = db.IntegerProperty(required = True)
    playerbet2 = db.IntegerProperty(required = True)
    playerbet3 = db.IntegerProperty(required = True)
    playerbet4 = db.IntegerProperty(required = True)
    dealerhand = db.StringListProperty(required = True)
    deck = db.StringListProperty(required = True)

    

# Create the WSGI application and define route handlers
app = WSGIApplication([
        Route(r'/', handler='modules.mainpage.MainPage', name='mainpage'),
        Route(r'/login', handler='modules.authentication.Login', name='login'),
        Route(r'/signup', handler='modules.authentication.SignUp', name='signup'),
        Route(r'/logout', handler='modules.authentication.Logout', name='logout'),
        Route(r'/newbj', handler='modules.game.NewBlackjack', name='newbj'),
        Route(r'/insurancebj', handler='modules.game.InsuranceBlackjack', name='insurancebj'),
        Route(r'/loseins', handler='modules.game.LoseInsurance', name='loseins'),
        Route(r'/playbj', handler='modules.game.PlayBlackjack', name='playbj'),
        Route(r'/resultsbj', handler='modules.game.ResultsBlackjack', name='resultsbj')], 
        debug=True)
'''
        

'''        

