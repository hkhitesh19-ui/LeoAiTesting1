import pyotp
from NorenRestApiPy.NorenApi import NorenApi

# Aapke Details
uid = 'FN177091'
pwd = 'Nilsky@2026'
vc = 'FN177091_U'
app_key = '21fc960fa7d6fe3d387bc3da23dabca3'
imei = 'abc1234'
totp_key = '7CC625GT4LZ3S2GXT22CH7AHKU736547'

api = NorenApi(host="https://api.shoonya.com/NorenWClientTP/", websocket="wss://api.shoonya.com/NorenWSTP/")

def test_login():
    try:
        # Step 1: Generate TOTP
        token = pyotp.TOTP(totp_key).now()
        print(f"Generated TOTP: {token}")

        # Step 2: Attempt Login
        res = api.login(userid=uid, password=pwd, twoFA=token, vendor_code=vc, api_secret=app_key, imei=imei)
        
        if res and res.get('stat') == 'Ok':
            print("✅ LOGIN SUCCESSFUL!")
            print(f"Welcome Name: {res.get('uname')}")
        else:
            print(f"❌ LOGIN FAILED: {res}")
    except Exception as e:
        print(f"⚠️ ERROR: {str(e)}")

if __name__ == "__main__":
    test_login()