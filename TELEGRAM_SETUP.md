# 📱 Telegram Alert Setup Guide

## Step 1: Create Telegram Bot

### 1.1 Open BotFather
1. Open Telegram app
2. Search for `@BotFather`
3. Start chat with `/start`

### 1.2 Create New Bot
```
/newbot
```

### 1.3 Follow Instructions
- Bot name: `Type F Trading Bot` (or any name)
- Username: `TypeFTradingBot` (must end with 'bot')

### 1.4 Save Your Token
You'll receive a message like:
```
Done! Your token is: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

**COPY THIS TOKEN** ✅

---

## Step 2: Get Your Chat ID

### 2.1 Start Chat with Your Bot
1. Click the link BotFather sends
2. Click "START" button

### 2.2 Get Chat ID (EASIEST METHOD ⭐)
**Method 1: Use @userinfobot (RECOMMENDED)**
1. Telegram par `@userinfobot` search karein
2. Bot ko `/start` bhejein
3. Wo aapko immediately aapki Chat ID dega (jaise `123456789`)
4. **COPY kar lein** ✅

**Method 2: Use GetIDsBot**
1. Search `@getidsbot` in Telegram
2. Start chat
3. It will send your Chat ID

**Method 3: Manual Method**
1. Send a message to your bot
2. Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
3. Look for `"chat":{"id": 123456789}`

**COPY YOUR CHAT ID** ✅

---

## Step 3: Set Environment Variables on Render

### 3.1 Go to Render Dashboard
https://dashboard.render.com

### 3.2 Select Your Service
Click on `leoaitesting1` (or your service name)

### 3.3 Go to Environment Tab
Click "Environment" in the left sidebar

### 3.4 Add Environment Variables

**Add Variable 1:**
- Key: `TELEGRAM_TOKEN`
- Value: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz` (your bot token)

**Add Variable 2:**
- Key: `TELEGRAM_CHAT_ID`
- Value: `123456789` (your chat ID)

### 3.5 Save Changes
Click "Save Changes" button

### 3.6 Redeploy
Render will automatically redeploy with new environment variables

---

## Step 4: Test Telegram Integration

### 4.1 Wait for Deployment
Wait 2-3 minutes for Render to redeploy

### 4.2 Test Alert
Open in browser:
```
https://leoaitesting1.onrender.com/telegram_test
```

### 4.3 Check Your Phone
You should receive: "🧪 Test Alert - Telegram integration is working! ✅"

---

## Step 5: Using Alerts in Your Code

### Entry Alert
```python
send_trade_entry_alert(
    symbol="NIFTY FUT",
    price=21500.00,
    sl=21400.00,
    strategy="Type F"
)
```

### Exit Alert
```python
send_trade_exit_alert(
    symbol="NIFTY FUT",
    entry=21500.00,
    exit=21650.00,
    pnl=150.00,
    reason="Target Hit"
)
```

### Error Alert
```python
send_error_alert("Connection timeout while placing order")
```

### Custom Alert
```python
send_telegram_alert("📊 *Daily Summary*\n\nTotal P&L: ₹5,000")
```

---

## Troubleshooting

### ❌ "Telegram Credentials missing!"
- Check environment variables are set on Render
- Variable names must be exact: `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID`
- Redeploy after adding variables

### ❌ "Telegram Error: Unauthorized"
- Your token is wrong
- Create a new bot or check token again

### ❌ "Telegram Error: Bad Request"
- Your Chat ID is wrong
- Get Chat ID again using GetIDsBot

### ❌ "Request timeout"
- Render server might be slow
- Check Render logs for errors

---

## 🎯 Pro Tips

1. **Test First**: Always test with `/telegram_test` endpoint before going live
2. **Rate Limits**: Telegram allows ~30 messages/second (way more than needed)
3. **Markdown**: Use `*bold*`, `_italic_`, `` `code` `` in messages
4. **Emojis**: Make alerts easy to spot 🚀 ✅ ❌ 📊
5. **Keep Token Secret**: Never commit token to GitHub

---

## 📱 Alert Examples

### Entry Signal
```
🚀 STRATEGY ALERT: ENTRY

Strategy: Type F
Symbol: NIFTY FUT
Entry Price: ₹21,500.00
Stop Loss: ₹21,400.00
Risk: ₹100.00

Time: 09:30:15 AM
```

### Exit Signal
```
✅ STRATEGY ALERT: EXIT

Symbol: NIFTY FUT
Entry: ₹21,500.00
Exit: ₹21,650.00
P&L: ₹150.00
Reason: Target Hit

Time: 02:45:30 PM
```

### Error Alert
```
🔴 BOT ERROR ALERT

Error: Connection timeout
Time: 10:15:00 AM

Please check the logs immediately!
```

---

## 🚀 Done!

Your Telegram alerts are now configured! Every trade, error, and update will be sent directly to your phone in real-time.

**Test URL**: https://leoaitesting1.onrender.com/telegram_test
