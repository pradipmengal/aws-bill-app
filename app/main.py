from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from app.services.aws_service import get_aws_cost_and_usage
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
