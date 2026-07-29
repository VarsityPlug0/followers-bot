# ============================================
# CONFIG — Follower Selling Bot
# ============================================

# --- Panel API ---
PANEL_API_URL = 'https://justanotherpanel.com/api/v2'
PANEL_API_KEY = 'fc23aad33a38ec354c4352b68ef462a6'

# --- Payment Settings ---
PAYPAL_ME_LINK = 'paypal.me/BevanNdzhaka'

# --- Telegram Bot ---
BOT_TOKEN = '8846997044:AAFHFa2v0I67WoWhNJwHkCxQMghS7pqYdEU'

# --- Admin ---
ADMIN_IDS = [8558050560]  # @BevanNdzhaka

# --- Service Mapping ---
SERVICES = {
    # Instagram Followers
    'ig_500':   {'panel_id': 1, 'quantity': 500,   'name': '500 IG Followers',    'price_cents': 1500},
    'ig_1000':  {'panel_id': 1, 'quantity': 1000,  'name': '1,000 IG Followers',  'price_cents': 2700},
    'ig_2500':  {'panel_id': 1, 'quantity': 2500,  'name': '2,500 IG Followers',  'price_cents': 5700},
    'ig_5000':  {'panel_id': 1, 'quantity': 5000,  'name': '5,000 IG Followers',  'price_cents': 9700},
    'ig_10000': {'panel_id': 1, 'quantity': 10000, 'name': '10,000 IG Followers', 'price_cents': 17700},

    # Instagram Likes
    'ig_likes_100':  {'panel_id': 2, 'quantity': 100,  'name': '100 IG Likes',   'price_cents': 500},
    'ig_likes_500':  {'panel_id': 2, 'quantity': 500,  'name': '500 IG Likes',   'price_cents': 1500},
    'ig_likes_1000': {'panel_id': 2, 'quantity': 1000, 'name': '1,000 IG Likes', 'price_cents': 2500},

    # TikTok Followers
    'tt_500':   {'panel_id': 3, 'quantity': 500,  'name': '500 TikTok Followers',   'price_cents': 1500},
    'tt_1000':  {'panel_id': 3, 'quantity': 1000, 'name': '1,000 TikTok Followers', 'price_cents': 2500},
    'tt_5000':  {'panel_id': 3, 'quantity': 5000, 'name': '5,000 TikTok Followers', 'price_cents': 9700},

    # TikTok Likes
    'tt_likes_100':  {'panel_id': 4, 'quantity': 100,  'name': '100 TikTok Likes',   'price_cents': 400},
    'tt_likes_500':  {'panel_id': 4, 'quantity': 500,  'name': '500 TikTok Likes',   'price_cents': 1200},
    'tt_likes_1000': {'panel_id': 4, 'quantity': 1000, 'name': '1,000 TikTok Likes', 'price_cents': 2200},
}
