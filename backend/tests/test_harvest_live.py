"""
Live end-to-end harvest diagnostic.
Run directly: python tests/test_harvest_live.py
NOT intended as a pytest test — it makes real HTTP/browser requests.
"""
import asyncio
import sys
from datetime import date

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


async def run_harvest_diagnostic():
    from harvesting.service import HarvestingService
    from harvesting.utils import get_ist_date

    today = get_ist_date()
    print(f"[TEST] Target date: {today}")

    svc = HarvestingService()
    svc.load_sources()
    sources = svc.get_sources()
    enabled = [s for s in sources if s.enabled]
    print(f"[TEST] Enabled sources ({len(enabled)}): {[s.id for s in enabled]}")

    # Test 1: pib_india — direct PDF, fastest test
    print("\n--- TEST: pib_india (direct_pdf) ---")
    result = await svc.run_harvest(
        target_date=today,
        source_ids=["pib_india"],
        triggered_by="test",
    )
    print(f"  successful={result.successful} failed={result.failed} duration={result.duration_seconds}s")
    for a in result.attempts:
        print(f"  [{a['source_id']}] status={a['status']} error={a.get('error_message') or ''}")

    # Test 2: dinamalar — Playwright source (Tamil)
    print("\n--- TEST: dinamalar (playwright) ---")
    result2 = await svc.run_harvest(
        target_date=today,
        source_ids=["dinamalar"],
        triggered_by="test",
    )
    print(f"  successful={result2.successful} failed={result2.failed} duration={result2.duration_seconds}s")
    for a in result2.attempts:
        print(f"  [{a['source_id']}] edition={a['edition_name']} status={a['status']} error={a.get('error_message') or ''}")

    # Test 3: dainik_jagran — Playwright (Hindi)
    print("\n--- TEST: dainik_jagran (playwright) ---")
    result3 = await svc.run_harvest(
        target_date=today,
        source_ids=["dainik_jagran"],
        triggered_by="test",
    )
    print(f"  successful={result3.successful} failed={result3.failed} duration={result3.duration_seconds}s")
    for a in result3.attempts:
        print(f"  [{a['source_id']}] edition={a['edition_name']} status={a['status']} error={a.get('error_message') or ''}")

    print("\n[DONE] Live harvest test complete.")


if __name__ == "__main__":
    asyncio.run(run_harvest_diagnostic())
