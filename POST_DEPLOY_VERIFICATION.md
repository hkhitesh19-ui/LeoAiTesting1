# ✅ Post-Deploy Verification Checklist

**Git Push:** ✅ SUCCESSFUL  
**GitHub Repo:** https://github.com/hkhitesh19-ui/LeoAiTesting1  
**Render Service:** https://dashboard.render.com/web/srv-d5i7u34hg0os738d70i0

---

## 🕐 Wait for Deploy (2-3 minutes)

### **Step 1: Monitor Render Dashboard**

1. Go to: https://dashboard.render.com/web/srv-d5i7u34hg0os738d70i0
2. Click **"Events"** tab
3. Wait for: `"Deploy live"` message ✅

### **Step 2: Check Logs**

Click **"Logs"** tab → Expected:

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

**NOT EXPECTED:**
```
❌ NameError: name 'get_live_ltp' is not defined  # This should be GONE!
```

---

## 🧪 Test Endpoints (After Deploy Complete)

### **Test 1: Start Endpoint**
```
https://leoaitesting1.onrender.com/start
```

**Expected Response:**
```json
{
  "ok": true,
  "message": "Bot started",
  "bot_connected": true,
  "status": "scanning"
}
```

### **Test 2: Health Endpoint**
```
https://leoaitesting1.onrender.com/health
```

**Expected Response:**
```json
{
  "ok": true,
  "running": false,
  "bot_connected": true,
  "last_run": "2026-01-13T...",
  "last_error": null,
  "has_active_trade": false,
  "timestamp": "2026-01-13T..."
}
```

### **Test 3: Get Status Endpoint (MAIN TEST!)**
```
https://leoaitesting1.onrender.com/get_status
```

**Expected Response:**
```json
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
    "ltp": 23456.78  ← LIVE PRICE (not 0.00!)
  },
  "tradeHistory": []
}
```

**SUCCESS INDICATOR:** `"ltp": 23456.78` (Real number, not 0.00)

### **Test 4: Dashboard**
```
Open your trading-dashboard.html
```

**Expected:**
- ✅ Heartbeat: Green (updating)
- ✅ Bot Status: "Searching" or "Active"
- ✅ Current LTP: ₹23,456.78 (updating every 5 sec)
- ✅ No "Internal Server Error"
- ✅ Flash animation on LTP change

---

## ❌ If Still Getting 500 Error

### **Possible Issues:**

1. **Render not auto-deploying from GitHub:**
   - Dashboard → Settings
   - Check: "Auto-Deploy" is **ON**
   - If OFF, click "Manual Deploy" → "Deploy latest commit"

2. **Old code cached:**
   - Dashboard → Settings
   - Click: **"Clear build cache & deploy"**

3. **Environment variables missing:**
   - Dashboard → Environment
   - Verify: UID, PWD, TOTP_KEY are set

4. **Dependencies not installed:**
   - Check Logs for: `pip install` errors
   - Verify requirements.txt has: NorenRestApiPy, pyotp, pandas

---

## ✅ Success Checklist

After deploy completes, verify:

- [ ] Render Logs show "Bot thread started"
- [ ] Render Logs show "Shoonya login successful"
- [ ] `/start` returns `{"ok": true}`
- [ ] `/health` returns `{"bot_connected": true}`
- [ ] `/get_status` returns LTP (not 0.00)
- [ ] Dashboard shows live LTP
- [ ] No 500 Internal Server Error
- [ ] Telegram bot responding to `/status`

---

## 🎯 Timeline

| Time | Action |
|------|--------|
| Now | Code pushed to GitHub ✅ |
| +30 sec | Render detects new commit |
| +1 min | Build starts |
| +2 min | Dependencies install |
| +3 min | Server starts |
| +3.5 min | Bot logs in to Shoonya |
| +4 min | **READY TO TEST!** ✅ |

---

## 📞 Next Steps

**Right Now:**
1. Open Render Dashboard
2. Watch "Events" tab for deploy progress
3. Check "Logs" tab for successful bot start

**After 3-4 Minutes:**
1. Test all 4 endpoints above
2. Open dashboard and verify LTP
3. Send Telegram `/status` command

**If All Tests Pass:**
🎉 **System is LIVE and WORKING!**

**If Issues:**
- Check this file for troubleshooting
- Share Render logs screenshot
- Check environment variables

---

**Abhi Render Dashboard kholo aur deploy progress dekho!** 🚀
