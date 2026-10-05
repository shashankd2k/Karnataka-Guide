import asyncio
import time
import httpx

URL = "http://localhost:11434/api/tags"  # or native ollama / docker ollama

async def benchmark_per_request():
    latencies = []
    for _ in range(5):
        t0 = time.perf_counter()
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("http://127.0.0.1:80/ready")
            assert resp.status_code == 200
        latencies.append((time.perf_counter() - t0) * 1000.0)
    return latencies

async def benchmark_persistent():
    latencies = []
    limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
    async with httpx.AsyncClient(timeout=5.0, limits=limits) as client:
        for _ in range(5):
            t0 = time.perf_counter()
            resp = await client.get("http://127.0.0.1:80/ready")
            assert resp.status_code == 200
            latencies.append((time.perf_counter() - t0) * 1000.0)
    return latencies

async def main():
    print("=== L1-D: Measuring HTTP Client Connection Reuse Benefit ===")
    per_req = await benchmark_per_request()
    pers = await benchmark_persistent()
    
    avg_per_req = sum(per_req) / len(per_req)
    avg_pers = sum(pers) / len(pers)
    saving_ms = avg_per_req - avg_pers
    
    print(f"Per-Request Client Mean: {avg_per_req:.2f} ms {per_req}")
    print(f"Persistent Client Mean:  {avg_pers:.2f} ms {pers}")
    print(f"Mean Socket/TCP Handshake Savings: {saving_ms:.2f} ms per call")
    print(f"Honest Assessment: ~{saving_ms:.1f} ms saved per turn (modest vs multi-second LLM inference, but eliminates connection thrashing).")

if __name__ == "__main__":
    asyncio.run(main())
