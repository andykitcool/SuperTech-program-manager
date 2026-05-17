import urllib.request, ssl

# HTTPS 测试
try:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request('https://print.lurevan.com/admin/login')
    r = urllib.request.urlopen(req, timeout=15, context=ctx)
    print(f"HTTPS print.lurevan.com -> {r.status} OK")
except Exception as e:
    print(f"HTTPS Error: {e}")

# HTTP 测试
try:
    r = urllib.request.urlopen('http://49.233.213.245:3000/admin/login', timeout=10)
    print(f"HTTP :3000 -> {r.status} OK")
except Exception as e:
    print(f"HTTP Error: {e}")

# API 测试
try:
    r = urllib.request.urlopen('http://49.233.213.245:8000/api/health', timeout=10)
    print(f"API :8000 -> {r.status} OK")
except Exception as e:
    print(f"API Error: {e}")
