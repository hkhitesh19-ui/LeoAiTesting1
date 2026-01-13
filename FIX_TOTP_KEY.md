# 🔧 Fix TOTP Key Format Issue

**Error:** `Login exception: Non-base32 digit found`  
**Problem:** `SHOONYA_API_SECRET` mein TOTP key sahi format mein nahi hai

---

## 🎯 **Problem Explained:**

TOTP key **base32 format** mein honi chahiye:
- ✅ Only letters: **A-Z** (uppercase)
- ✅ Only numbers: **2-7** (NOT 0, 1, 8, 9)
- ✅ No spaces, no special characters
- ✅ Length: Usually 16-32 characters

**Example Valid TOTP Key:**
```
JBSWY3DPEHPK3PXP
ABCDEFGHIJKLMNOP
234567ABCDEFGHIJ
```

**Invalid Examples:**
```
❌ JBSWY3DPEHPK3PXP123  (has 0,1,8,9)
❌ jbswy3dpehpk3pxp     (lowercase)
❌ JBSWY 3DPE HPK3PXP  (has spaces)
❌ JBSWY-3DPE-HPK3PXP  (has special chars)
```

---

## ✅ **Solution: Get Correct TOTP Key from Shoonya**

### **Method 1: Shoonya Web Dashboard**

1. **Login to Shoonya:**
   ```
   https://shoonya.finvasia.com
   ```

2. **Go to API Settings:**
   - Profile/Settings → **API** section
   - Or direct: https://shoonya.finvasia.com/settings/api

3. **Generate New TOTP Key:**
   - Look for **"TOTP Secret"** or **"API Key"**
   - Click **"Generate"** or **"Create New Key"**
   - You'll see:
     - QR Code (for authenticator apps)
     - **Base32 String** (THIS is what you need!)

4. **Copy the Base32 String:**
   ```
   Format: JBSWY3DPEHPK3PXP (16-32 chars, A-Z, 2-7 only)
   
   ⚠️ IMPORTANT:
   - Copy the STRING, not QR code
   - Copy FULL string (no spaces)
   - Should be uppercase automatically
   ```

5. **Update in Render:**
   - Go to: https://dashboard.render.com/web/srv-d5i7u34hg0os738d70i0/env
   - Find: `SHOONYA_API_SECRET`
   - Click **Edit** (pencil icon)
   - **Delete old value**
   - **Paste new base32 string**
   - Click **Save**

---

### **Method 2: If You Have QR Code Only**

**If Shoonya ne sirf QR code diya hai:**

1. **Use QR Code Scanner:**
   - Install: Google Authenticator app
   - Scan QR code
   - Get 6-digit code

2. **Extract Base32 from QR:**
   - QR code mein base32 string encoded hoti hai
   - Use online tool: https://zxing.org/w/decode.jspx
   - Upload QR code image
   - Extract the `otpauth://totp/...?secret=XXXXX` part
   - `secret=` ke baad jo value hai woh TOTP key hai!

3. **Or Contact Shoonya Support:**
   - Email: api@finvasia.com
   - Request: "Please provide TOTP Secret Key in base32 format"
   - They'll send you the string directly

---

### **Method 3: Check Current Value Format**

**Render mein current value check karo:**

1. Go to: https://dashboard.render.com/web/srv-d5i7u34hg0os738d70i0/env
2. Find: `SHOONYA_API_SECRET`
3. Click **eye icon** to reveal value
4. Check format:

**If it looks like:**
```
✅ JBSWY3DPEHPK3PXP        → Correct format!
✅ ABCDEFGHIJKLMNOP        → Correct format!
✅ 234567ABCDEFGHIJ        → Correct format!

❌ jbswy3dpehpk3pxp        → Convert to uppercase
❌ JBSWY 3DPE HPK3PXP     → Remove spaces
❌ JBSWY-3DPE-HPK3PXP     → Remove special chars
❌ 1234567890              → Has invalid digits (0,1,8,9)
❌ otpauth://totp/...      → This is URL, extract secret part
```

---

## 🔧 **Quick Fix Steps:**

### **Step 1: Get Correct TOTP Key**
- Shoonya dashboard se base32 string copy karo
- Ya support se request karo

### **Step 2: Update in Render**
```
1. Render Dashboard → Environment
2. SHOONYA_API_SECRET → Edit
3. Delete old value
4. Paste new base32 string
5. Save
```

### **Step 3: Wait for Auto-Deploy**
- 30-60 seconds wait karo
- Service automatically restart hoga

### **Step 4: Verify**
```
Check logs:
✅ "Shoonya login successful"

Test endpoint:
https://leoaitesting1.onrender.com/get_status
→ Should show: "ltp": 23456.78 (not 0.0)
```

---

## 📋 **TOTP Key Format Checklist:**

Before saving in Render, verify:

- [ ] Only uppercase letters (A-Z)
- [ ] Only digits 2-7 (NO 0, 1, 8, 9)
- [ ] No spaces
- [ ] No special characters (-, _, /, etc.)
- [ ] Length: 16-32 characters
- [ ] Example: `JBSWY3DPEHPK3PXP`

---

## 🆘 **If Still Not Working:**

### **Check Render Logs:**
After updating TOTP key, check logs for:

**Success:**
```
✅ Shoonya login successful! Session: xxx...
```

**Still Error:**
```
❌ TOTP_KEY invalid format (must be base32: A-Z, 2-7 only)
```

**If error persists:**
1. Double-check TOTP key format
2. Ensure no extra spaces/characters
3. Try regenerating TOTP key from Shoonya
4. Contact Shoonya support for correct format

---

## 💡 **Common Mistakes:**

| Mistake | Fix |
|---------|-----|
| Lowercase letters | Convert to UPPERCASE |
| Has spaces | Remove all spaces |
| Has 0,1,8,9 | Only use 2-7 |
| Special characters | Remove -, _, /, etc. |
| QR code URL | Extract secret part only |
| Too short/long | Should be 16-32 chars |

---

## ✅ **After Fix:**

**Expected Logs:**
```
✅ Shoonya login successful! Session: xxx...
✅ Found NIFTY Future: NIFTY26JAN, Token: 12345
✅ Bot initialization complete
```

**Expected Response:**
```json
{
  "activeTrade": {
    "ltp": 23456.78  ← Live price!
  },
  "last_error": null  ← No error!
}
```

---

**TOTP key update karo aur 1 minute baad test karo!** 🔧
