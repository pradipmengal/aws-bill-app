from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from app.services.aws_service import get_aws_cost_and_usage
from botocore.exceptions import ClientError
from typing import Optional
import os

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
