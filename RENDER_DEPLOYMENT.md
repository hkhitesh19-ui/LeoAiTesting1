# 🚀 Render Deployment Guide - Type F Trading Bot

**Status:** Complete System Ready ✅  
**Last Updated:** 13 January 2026

---

## 📦 **Files Required for Deployment**

Your workspace now has all necessary files:

```
F:\LeoAi_Testing_Cursor\
├── api_server.py          # FastAPI server with LTP fetching
├── bot.py                 # Main trading bot with Shoonya integration
├── strategy_scanner.py    # Excel logging
├── requirements.txt       # All dependencies
├── trading-dashboard.html # Frontend dashboard
└── RENDER_DEPLOYMENT.md   # This file
```

---

## 🔧 **Step 1: Render Environment Variables**

Login to Render Dashboard → Your Service → Environment

Add these variables:

```bash
# Shoonya API Credentials (REQUIRED)
UID=<Your Shoonya User ID>
PWD=<Your Shoonya Password>
TOTP_KEY=<Your TOTP Secret Key>

# Shoonya API Config (Optional - defaults provided)
VENDOR_CODE=NA
APP_KEY=
IMEI=abc1234

# Telegram Alerts (REQUIRED for notifications)
TELEGRAM_TOKEN=<Your Bot Token from @BotFather>
TELEGRAM_CHAT_ID=<Your Chat ID>
```

### How to Get Credentials:

#### **Shoonya Credentials:**
1. Login to https://shoonya.finvasia.com
2. Go to Settings → API
3. Note down your UID, PWD
4. Generate TOTP Key (save it securely!)

#### **Telegram Credentials:**
1. Message @BotFather on Telegram
2. Create new bot: `/newbot`
3. Copy the `TELEGRAM_TOKEN`
4. Message @userinfobot to get your `TELEGRAM_CHAT_ID`

---

## 🚀 **Step 2: Deploy to Render**

### **Option A: Git Deploy (Recommended)**

```bash
# 1. Initialize Git (if not already)
git init
git add .
git commit -m "Complete trading bot system"

# 2. Push to GitHub
git remote add origin https://github.com/yourusername/trading-bot.git
git push -u origin main

# 3. On Render Dashboard:
- Click "New+" → "Web Service"
- Connect your GitHub repo
- Build Command: pip install -r requirements.txt
- Start Command: uvicorn api_server:app --host 0.0.0.0 --port $PORT
```

### **Option B: Manual Deploy**

1. Zip all files: `api_server.py`, `bot.py`, `strategy_scanner.py`, `requirements.txt`
2. Upload to Render via Dashboard
3. Set start command: `uvicorn api_server:app --host 0.0.0.0 --port $PORT`

---

## ✅ **Step 3: Verify Deployment**

### **Check Render Logs:**

Expected logs on successful deployment:

```
✅ Successfully imported trade_data and api from bot.py
✅ Bot thread started
🤖 Type F Trading Bot Started
==================================================
🔐 Logging in to Shoonya with UID: YOUR_UID
✅ Shoonya login successful! Session: xxx...
✅ Found NIFTY Future: NIFTY26JAN, Token: 12345
✅ Bot initialization complete
🔍 Starting strategy scanner...
==================================================
🤖 Telegram Emergency Stop Bot started!
✅ Telegram alerts initialized
```

### **If You See Errors:**

❌ **"bot.py not found. Using mock trade_data."**
- File not uploaded properly. Re-deploy all files.

❌ **"Missing credentials! Set UID, PWD, TOTP_KEY"**
- Environment variables not set. Check Render Environment tab.

❌ **"Shoonya login failed"**
- Check UID, PWD, TOTP_KEY are correct
- TOTP_KEY should be base32 string (like `JBSWY3DPEHPK3PXP`)

❌ **"Telegram bot error"**
- Check TELEGRAM_TOKEN and TELEGRAM_CHAT_ID
- Token format: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`

---

## 🔍 **Step 4: Test the System**

### **Test 1: API Health Check**

```bash
# Open in browser:
https://your-app.onrender.com/health

# Expected response:
{
  "ok": true,
  "running": false,
  "bot_connected": true,
  "last_run": "2026-01-13T09:15:00",
  "last_error": null,
  "has_active_trade": false,
  "timestamp": "2026-01-13T09:15:30.123456"
}
```

**Key Field:** `bot_connected: true` ✅

### **Test 2: Get Status Endpoint**

```bash
# Open in browser:
https://your-app.onrender.com/get_status

# Expected response:
{
  "botStatus": {
    "status": "Searching",
    "message": "Scanning"
  },
  "todayPnl": 0.0,
  "pnlPercentage": 0.0,
  "activeTrade": {
    "symbol": "NIFTY26JAN",
    "entry": 0.0,
    "sl": 0.0,
    "ltp": 23500.50  # ← Should show LIVE price, not 0.00!
  },
  "tradeHistory": []
}
```

**Key Field:** `activeTrade.ltp` should show live NIFTY price (during market hours)

### **Test 3: Telegram Alerts**

```bash
# Open in browser:
https://your-app.onrender.com/telegram_test

# Check your Telegram - you should receive:
"🧪 Test Alert
Telegram integration is working! ✅"
```

### **Test 4: Telegram Commands**

Send these to your bot on Telegram:

```
/status     → Should show current bot status
/help       → List all commands
/stop       → Emergency exit (use carefully!)
```

---

## 📊 **Step 5: Connect Frontend Dashboard**

Your `trading-dashboard.html` is already configured:

```javascript
// Line 352
const API_URL = 'https://leoaitesting1.onrender.com/get_status';
```

### **Deploy Options:**

#### **Option A: Netlify (Already Done)**
- Your dashboard is already live on Netlify
- Just ensure API_URL points to your Render backend

#### **Option B: GitHub Pages**
```bash
# Push to GitHub
git add trading-dashboard.html
git commit -m "Dashboard"
git push

# Enable GitHub Pages in repo settings
# Access at: https://yourusername.github.io/trading-bot/trading-dashboard.html
```

#### **Option C: Local Testing**
```bash
# Just open the HTML file in browser
# It will connect to your Render backend automatically
```

---

## 🎯 **LTP (Last Traded Price) Troubleshooting**

### **Problem:** Dashboard shows LTP as ₹0.00

### **Solution Checklist:**

#### ✅ **1. Check Bot Connection**
```bash
# Render Logs should show:
✅ Successfully imported trade_data and api from bot.py
✅ Bot thread started

# If not, bot.py failed to import/start
```

#### ✅ **2. Check Shoonya Login**
```bash
# Render Logs should show:
✅ Shoonya login successful!
✅ Found NIFTY Future: NIFTY26JAN, Token: 12345

# If not, check credentials in Environment Variables
```

#### ✅ **3. Check Market Hours**
```
NSE Trading Hours: 9:15 AM - 3:30 PM (Monday - Friday)

Outside market hours:
- LTP will show last known price or 0.00
- This is NORMAL behavior
```

#### ✅ **4. Check Token Availability**
```bash
# In Render logs, look for:
✅ Found NIFTY Future: NIFTY26JAN, Token: XXXXX

# If you see:
⚠️ Could not find current month NIFTY future

# Solution: Token search logic may need adjustment
# NIFTY futures roll over on last Thursday of each month
```

#### ✅ **5. Manual LTP Test**
```bash
# SSH into Render shell (if available) or add debug endpoint

# Add this to api_server.py:
@app.get("/debug_ltp")
async def debug_ltp():
    from bot import api, trade_data
    token = trade_data.get("fut_token")
    
    if not token:
        return {"error": "Token not found"}
    
    try:
        res = api.get_quotes(exchange='NFO', token=str(token))
        return {
            "token": token,
            "raw_response": res,
            "ltp": res.get('lp', 0.0) if res else None
        }
    except Exception as e:
        return {"error": str(e)}

# Test: https://your-app.onrender.com/debug_ltp
```

---

## 📈 **Expected LTP Behavior**

### **During Market Hours (9:15 AM - 3:30 PM):**
- ✅ LTP should update every 5 seconds
- ✅ Price should match NIFTY Futures on NSE
- ✅ Flash animation on dashboard when price changes

### **Outside Market Hours:**
- ⚠️ LTP may show 0.00 (API returns no data)
- ⚠️ Or shows last traded price from market close
- This is NORMAL - not an error!

### **Weekends/Holidays:**
- ⚠️ Market closed, LTP will be 0.00
- Bot will continue running but won't find signals

---

## 🔥 **Production Checklist**

Before going live with real money:

- [ ] All environment variables set correctly
- [ ] Shoonya login successful (check logs)
- [ ] LTP showing live price during market hours
- [ ] Telegram alerts working (`/telegram_test`)
- [ ] Dashboard heartbeat green and updating
- [ ] `/status` command responding on Telegram
- [ ] Emergency `/stop` command tested (in demo mode)
- [ ] Trade history logging to Excel working
- [ ] Risk per trade configured properly in `bot.py`
- [ ] Stop loss logic tested in paper trading
- [ ] Overnight position handling understood (for swing trading)

---

## ⚠️ **Important Notes**

### **1. File Persistence on Render**
```
Excel logs (Type_F_Trading_Logs.xlsx) are TEMPORARY!
Files will be deleted on server restart.

Solutions:
- Use Google Sheets (recommended for swing trading)
- Use MongoDB/PostgreSQL (production grade)
- Use Render Persistent Disk (paid feature)
```

### **2. Server Sleep (Free Tier)**
```
Render free tier:
- Server sleeps after 15 minutes of inactivity
- First request after sleep takes 30-60 seconds

Solution:
- Upgrade to paid tier ($7/month)
- Or use external cron job to ping /health every 10 minutes
```

### **3. Market Data Limits**
```
Shoonya API has rate limits:
- Don't call get_quotes more than once per second
- Current bot calls every 5 seconds (safe)
```

### **4. Emergency Stop**
```
Three ways to stop bot:
1. Telegram: /stop command
2. Render Dashboard: Suspend service
3. Environment Variable: Set EMERGENCY_STOP=true
```

---

## 🆘 **Support & Debugging**

### **Common Issues:**

#### **Issue:** Bot not starting
```bash
# Check:
1. All files deployed (bot.py, api_server.py, strategy_scanner.py)
2. requirements.txt has all dependencies
3. Start command correct: uvicorn api_server:app --host 0.0.0.0 --port $PORT
```

#### **Issue:** Login failing
```bash
# Check:
1. UID is correct (usually 6-10 characters)
2. PWD is URL-encoded if it has special characters
3. TOTP_KEY is base32 format (not QR code!)
4. Time sync is correct on Render servers (usually automatic)
```

#### **Issue:** LTP always 0.00 (during market hours)
```bash
# Check:
1. bot_connected: true in /health endpoint
2. fut_token is not null in trade_data
3. api.get_quotes() not throwing exceptions (check logs)
4. Market is actually open (NSE holidays: check calendar)
```

---

## 🎉 **Success Indicators**

Your system is fully operational when you see:

✅ **Render Logs:**
```
✅ Bot thread started
✅ Shoonya login successful
✅ Found NIFTY Future: NIFTY26JAN
✅ Telegram Emergency Stop Bot started!
```

✅ **Dashboard:**
```
🟢 Heartbeat: Green (updating every 5 seconds)
📊 Bot Status: "Active" or "Searching"
💹 LTP: Live price (not ₹0.00)
📱 Last Sync: Within 10 seconds
```

✅ **Telegram:**
```
🟢 Bot is now ONLINE!
/status command responding
/help showing all commands
```

---

## 🚀 **You're Ready to Go Live!**

**Final Steps:**
1. Monitor for 1-2 days in market hours
2. Verify LTP updates correctly
3. Test one manual trade (small quantity)
4. Enable full automation

**Trading Hours:** 9:15 AM - 3:30 PM (NSE)  
**Best Start Time:** 9:30 AM (after opening volatility settles)

---

**Good Luck Trading! 📈💰**

*For issues, check Render logs first. Most problems are visible there.*
