import httpx
import asyncio
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"

async def test_backend():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # 1. Health Check
        logger.info("Testing /health...")
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        logger.info("✅ /health passed")

        # Prepare headers for demo mode
        headers = {"x-use-demo-data": "true"}
        
        # Date range for testing
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        params = {"start_date": start_date, "end_date": end_date}

        # 2. Daily Cost
        logger.info("Testing /daily-cost...")
        response = await client.get("/daily-cost", headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            assert "daily_costs" in data
            logger.info(f"✅ /daily-cost passed with {len(data['daily_costs'])} records")
        else:
            logger.error(f"❌ /daily-cost failed: {response.status_code} - {response.text}")

        # 3. Service Cost
        logger.info("Testing /service-cost...")
        response = await client.get("/service-cost", headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            assert "services" in data
            logger.info(f"✅ /service-cost passed with {len(data['services'])} services")
        else:
            logger.error(f"❌ /service-cost failed: {response.status_code} - {response.text}")

        # 4. Region Cost
        logger.info("Testing /region-cost...")
        response = await client.get("/region-cost", headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            assert "regions" in data
            logger.info(f"✅ /region-cost passed with {len(data['regions'])} regions")
        else:
            logger.error(f"❌ /region-cost failed: {response.status_code} - {response.text}")

        # 5. Region Service Breakdown
        logger.info("Testing /region-service-breakdown...")
        response = await client.get("/region-service-breakdown", headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            assert "regions" in data
            logger.info("✅ /region-service-breakdown passed")
        else:
            logger.error(f"❌ /region-service-breakdown failed: {response.status_code} - {response.text}")

        # 6. Usage API
        logger.info("Testing /api/usage...")
        response = await client.get("/api/usage", headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            assert "regions" in data
            assert "consolidated" in data
            logger.info("✅ /api/usage passed")
        else:
            logger.error(f"❌ /api/usage failed: {response.status_code} - {response.text}")

if __name__ == "__main__":
    try:
        asyncio.run(test_backend())
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
