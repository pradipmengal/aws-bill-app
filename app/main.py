from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from app.services.aws_service import (
    get_aws_cost_and_usage, 
    get_aws_daily_usage, 
    get_aws_resource_usage,
    get_daily_cost,
    get_service_cost,
    get_region_cost,
    get_region_service_breakdown
)
from botocore.exceptions import ClientError
from typing import Optional
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="AWS Region-wise Billing Dashboard")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/help")
async def read_help(request: Request):
    return templates.TemplateResponse("help.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.info("Health check requested")
    return {"status": "ok"}

@app.get("/daily-cost")
async def get_daily_cost_endpoint(request: Request):
    """Get daily cost for the last 7 days"""
    try:
        logger.info("Daily cost endpoint called")
        
        # Extract credentials from headers
        access_key = request.headers.get('x-aws-access-key-id')
        secret_key = request.headers.get('x-aws-secret-access-key')
        use_demo = request.headers.get('x-use-demo-data') == 'true'

        data = get_daily_cost(
            access_key=access_key,
            secret_key=secret_key,
            force_demo=use_demo
        )
        
        logger.info(f"Daily cost data retrieved successfully: {len(data.get('daily_costs', []))} days")
        return data
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        logger.error(f"AWS ClientError in daily-cost: {error_code} - {error_msg}")
        
        if error_code in ['UnrecognizedClientException', 'InvalidClientTokenId', 'AuthFailure', 'InvalidAccessKeyId', 'SignatureDoesNotMatch']:
            raise HTTPException(status_code=401, detail="Invalid AWS credentials. Please double-check your Access Key and Secret Key.")
        elif error_code == 'AccessDeniedException':
            raise HTTPException(status_code=403, detail="Access denied. Your AWS user needs 'ce:GetCostAndUsage' permissions.")
        else:
            raise HTTPException(status_code=500, detail=f"AWS error: {error_msg}")
            
    except Exception as e:
        logger.error(f"Error in daily-cost endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/service-cost")
async def get_service_cost_endpoint(request: Request):
    """Get service-wise cost breakdown"""
    try:
        logger.info("Service cost endpoint called")
        
        # Extract credentials from headers
        access_key = request.headers.get('x-aws-access-key-id')
        secret_key = request.headers.get('x-aws-secret-access-key')
        use_demo = request.headers.get('x-use-demo-data') == 'true'

        data = get_service_cost(
            access_key=access_key,
            secret_key=secret_key,
            force_demo=use_demo
        )
        
        logger.info(f"Service cost data retrieved successfully: {len(data.get('services', {}))} services")
        return data
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        logger.error(f"AWS ClientError in service-cost: {error_code} - {error_msg}")
        
        if error_code in ['UnrecognizedClientException', 'InvalidClientTokenId', 'AuthFailure', 'InvalidAccessKeyId', 'SignatureDoesNotMatch']:
            raise HTTPException(status_code=401, detail="Invalid AWS credentials. Please double-check your Access Key and Secret Key.")
        elif error_code == 'AccessDeniedException':
            raise HTTPException(status_code=403, detail="Access denied. Your AWS user needs 'ce:GetCostAndUsage' permissions.")
        else:
            raise HTTPException(status_code=500, detail=f"AWS error: {error_msg}")
            
    except Exception as e:
        logger.error(f"Error in service-cost endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/region-cost")
async def get_region_cost_endpoint(request: Request):
    """Get region-wise cost breakdown"""
    try:
        logger.info("Region cost endpoint called")
        
        # Extract credentials from headers
        access_key = request.headers.get('x-aws-access-key-id')
        secret_key = request.headers.get('x-aws-secret-access-key')
        use_demo = request.headers.get('x-use-demo-data') == 'true'

        data = get_region_cost(
            access_key=access_key,
            secret_key=secret_key,
            force_demo=use_demo
        )
        
        logger.info(f"Region cost data retrieved successfully: {len(data.get('regions', {}))} regions")
        return data
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        logger.error(f"AWS ClientError in region-cost: {error_code} - {error_msg}")
        
        if error_code in ['UnrecognizedClientException', 'InvalidClientTokenId', 'AuthFailure', 'InvalidAccessKeyId', 'SignatureDoesNotMatch']:
            raise HTTPException(status_code=401, detail="Invalid AWS credentials. Please double-check your Access Key and Secret Key.")
        elif error_code == 'AccessDeniedException':
            raise HTTPException(status_code=403, detail="Access denied. Your AWS user needs 'ce:GetCostAndUsage' permissions.")
        else:
            raise HTTPException(status_code=500, detail=f"AWS error: {error_msg}")
            
    except Exception as e:
        logger.error(f"Error in region-cost endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/region-service-breakdown")
async def get_region_service_breakdown_endpoint(request: Request):
    """Get region-wise cost breakdown with service details"""
    try:
        logger.info("Region-service breakdown endpoint called")
        
        # Extract credentials from headers
        access_key = request.headers.get('x-aws-access-key-id')
        secret_key = request.headers.get('x-aws-secret-access-key')
        use_demo = request.headers.get('x-use-demo-data') == 'true'

        data = get_region_service_breakdown(
            access_key=access_key,
            secret_key=secret_key,
            force_demo=use_demo
        )
        
        logger.info(f"Region-service breakdown retrieved successfully: {len(data.get('regions', {}))} regions")
        return data
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        logger.error(f"AWS ClientError in region-service-breakdown: {error_code} - {error_msg}")
        
        if error_code in ['UnrecognizedClientException', 'InvalidClientTokenId', 'AuthFailure', 'InvalidAccessKeyId', 'SignatureDoesNotMatch']:
            raise HTTPException(status_code=401, detail="Invalid AWS credentials. Please double-check your Access Key and Secret Key.")
        elif error_code == 'AccessDeniedException':
            raise HTTPException(status_code=403, detail="Access denied. Your AWS user needs 'ce:GetCostAndUsage' permissions.")
        else:
            raise HTTPException(status_code=500, detail=f"AWS error: {error_msg}")
            
    except Exception as e:
        logger.error(f"Error in region-service-breakdown endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/billing")
async def get_billing(
    request: Request,
    start_date: str,
    end_date: str,
    granularity: str = "MONTHLY"
):
    try:
        # Extract credentials from headers
        access_key = request.headers.get('x-aws-access-key-id')
        secret_key = request.headers.get('x-aws-secret-access-key')
        use_demo = request.headers.get('x-use-demo-data') == 'true'

        data = get_aws_cost_and_usage(
            start_date, 
            end_date, 
            granularity,
            access_key=access_key,
            secret_key=secret_key,
            force_demo=use_demo
        )
        
        # Add daily usage
        daily_data = get_aws_daily_usage(
            access_key=access_key,
            secret_key=secret_key,
            force_demo=use_demo
        )
        data['daily_cost'] = daily_data['daily_cost']
        
        return data
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        
        if error_code in ['UnrecognizedClientException', 'InvalidClientTokenId', 'AuthFailure', 'InvalidAccessKeyId', 'SignatureDoesNotMatch']:
            raise HTTPException(status_code=401, detail="Invalid AWS credentials. Please double-check your Access Key and Secret Key.")
        elif error_code == 'AccessDeniedException':
            raise HTTPException(status_code=403, detail="Access denied. Your AWS user needs 'ce:GetCostAndUsage' permissions to view billing data.")
        else:
            raise HTTPException(status_code=500, detail="An unexpected AWS error occurred. Please try again later.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/usage")
async def read_usage(request: Request):
    return templates.TemplateResponse("usage.html", {"request": request})

@app.get("/api/usage")
async def get_usage(
    request: Request,
    start_date: str,
    end_date: str
):
    try:
        # Extract credentials from headers
        access_key = request.headers.get('x-aws-access-key-id')
        secret_key = request.headers.get('x-aws-secret-access-key')
        use_demo = request.headers.get('x-use-demo-data') == 'true'

        data = get_aws_resource_usage(
            start_date, 
            end_date,
            access_key=access_key,
            secret_key=secret_key,
            force_demo=use_demo
        )
        return data
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code in ['UnrecognizedClientException', 'InvalidClientTokenId', 'AuthFailure', 'InvalidAccessKeyId', 'SignatureDoesNotMatch']:
            raise HTTPException(status_code=401, detail="Invalid AWS credentials.")
        elif error_code == 'AccessDeniedException':
            raise HTTPException(status_code=403, detail="Access denied.")
        else:
            raise HTTPException(status_code=500, detail="An unexpected AWS error occurred.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
