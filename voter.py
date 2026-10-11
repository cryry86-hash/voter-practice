import asyncio
import aiohttp
import sys

# Force immediate log output so live progress updates in the console
sys.stdout.reconfigure(line_buffering=True)

# ==============================================================================
# OFFICIAL FORM CONFIGURATION
# ==============================================================================
FORM_URL = "https://docs.google.com/forms/u/0/d/e/1FAIpQLScz_QHD9DxFjZcOygSCCuUq_rd6nb2bIfAJxTaoOlZHfIInXA/formResponse"
ENTRY_ID = "entry.735219103"
CHOICE_VALUE = "Kokushibo"
TARGET_VOTES = 1000             # Capped at 100,000 votes per run
CONCURRENT_LIMIT = 12             # Smooth rate to prevent HTTP 429 errors
# ==============================================================================

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/x-www-form-urlencoded"
}

data = {
    ENTRY_ID: CHOICE_VALUE
}

async def send_vote(session, semaphore, stats):
    async with semaphore:
        success = False
        attempts = 0
        
        while not success and attempts < 3:
            attempts += 1
            try:
                async with session.post(FORM_URL, data=data, headers=headers, timeout=10, allow_redirects=False) as resp:
                    if resp.status in (200, 302):
                        stats["success"] += 1
                        success = True
                    elif resp.status == 429:
                        stats["last_error"] = "HTTP 429 (Rate Limited - backing off)"
                        await asyncio.sleep(2.0)
                    else:
                        stats["last_error"] = f"HTTP {resp.status}"
                        await asyncio.sleep(0.5)
            except Exception as e:
                stats["last_error"] = str(e)
                await asyncio.sleep(0.5)

        if not success:
            stats["failed"] += 1

        await asyncio.sleep(0.1)

        total = stats["success"] + stats["failed"]
        if total % 500 == 0 or total == TARGET_VOTES:
            err = f" | Last Status: {stats['last_error']}" if stats['last_error'] else ""
            print(f"--> [PROGRESS] {total:,}/{TARGET_VOTES:,} | Successful: {stats['success']:,} | Failed: {stats['failed']:,}{err}", flush=True)

async def main():
    print("==================================================", flush=True)
    print(f"🚀 OFFICIAL VOTER RUNNER | Target: {TARGET_VOTES:,} votes", flush=True)
    print(f"🎯 Target URL: {FORM_URL}", flush=True)
    print(f"📌 Entry ID: {ENTRY_ID} = {CHOICE_VALUE}", flush=True)
    print("==================================================", flush=True)

    semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)
    stats = {"success": 0, "failed": 0, "last_error": None}

    connector = aiohttp.TCPConnector(limit=30, ttl_dns_cache=300)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        batch_size = 2500
        for _ in range(0, TARGET_VOTES, batch_size):
            remaining = TARGET_VOTES - (stats["success"] + stats["failed"])
            if remaining <= 0:
                break
                
            current_batch = min(batch_size, remaining)
            tasks = [send_vote(session, semaphore, stats) for _ in range(current_batch)]
            await asyncio.gather(*tasks)

    print("==================================================", flush=True)
    print(f"🎉 RUN COMPLETE! Successful: {stats['success']:,} | Failed: {stats['failed']:,}", flush=True)
    print("==================================================", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
