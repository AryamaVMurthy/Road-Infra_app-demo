
import httpx
import asyncio
import sys

async def test_audit():
    print("Starting Audit Test...")
    async with httpx.AsyncClient(base_url="http://localhost:8088") as client:
        # 1. Login
        print("Logging in as SysAdmin...")
        resp = await client.post("/api/v1/auth/google-mock", params={"email": "sysadmin@marg.gov.in"})
        if resp.status_code != 200:
            print(f"Login Failed: {resp.status_code} {resp.text}")
            sys.exit(1)
        
        print("Login Successful. Cookies:", client.cookies)
        
        # 2. Get Audit All
        print("Fetching Audit Logs...")
        resp = await client.get("/api/v1/analytics/audit-all")
        if resp.status_code != 200:
            print(f"Audit Fetch Failed: {resp.status_code} {resp.text}")
            sys.exit(1)
            
        data = resp.json()
        print(f"Audit Fetch Successful. Count: {len(data)}")
        # print("First 2 logs:", data[:2])

if __name__ == "__main__":
    asyncio.run(test_audit())
