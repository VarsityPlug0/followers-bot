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
# panel_id verified against justanotherpanel.com API
SERVICES = {
    # Instagram Followers — ID 1810: USA Mix, 30D Refill, $4.75/1K, Max 200K
    'ig_500':   {'panel_id': 1810, 'quantity': 500,   'name': '500 IG Followers',    'price_cents': 1500},
    'ig_1000':  {'panel_id': 1810, 'quantity': 1000,  'name': '1,000 IG Followers',  'price_cents': 2700},
    'ig_2500':  {'panel_id': 1810, 'quantity': 2500,  'name': '2,500 IG Followers',  'price_cents': 5700},
    'ig_5000':  {'panel_id': 1810, 'quantity': 5000,  'name': '5,000 IG Followers',  'price_cents': 9700},
    'ig_10000': {'panel_id': 1810, 'quantity': 10000, 'name': '10,000 IG Followers', 'price_cents': 17700},

    # Instagram Likes — ID 1910: USA Mix, 30D Refill, $1.68/1K, Max 100K
    'ig_likes_100':  {'panel_id': 1910, 'quantity': 100,  'name': '100 IG Likes',   'price_cents': 500},
    'ig_likes_500':  {'panel_id': 1910, 'quantity': 500,  'name': '500 IG Likes',   'price_cents': 1500},
    'ig_likes_1000': {'panel_id': 1910, 'quantity': 1000, 'name': '1,000 IG Likes', 'price_cents': 2500},

    # TikTok Followers — ID 8777: 30D Refill, $1.25/1K, Max 100M
    'tt_500':   {'panel_id': 8777, 'quantity': 500,  'name': '500 TikTok Followers',   'price_cents': 1500},
    'tt_1000':  {'panel_id': 8777, 'quantity': 1000, 'name': '1,000 TikTok Followers', 'price_cents': 2500},
    'tt_5000':  {'panel_id': 8777, 'quantity': 5000, 'name': '5,000 TikTok Followers', 'price_cents': 9700},

    # TikTok Likes — ID 10023: 30D Refill, $0.02/1K, Max 1M
    'tt_likes_100':  {'panel_id': 10023, 'quantity': 100,  'name': '100 TikTok Likes',   'price_cents': 400},
    'tt_likes_500':  {'panel_id': 10023, 'quantity': 500,  'name': '500 TikTok Likes',   'price_cents': 1200},
    'tt_likes_1000': {'panel_id': 10023, 'quantity': 1000, 'name': '1,000 TikTok Likes', 'price_cents': 2200},
}
