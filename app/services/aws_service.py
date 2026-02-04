import boto3
from botocore.exceptions import ClientError
import os
import random
from datetime import datetime, timedelta

def get_aws_cost_and_usage(
    start_date: str, 
    end_date: str, 
    granularity: str = "MONTHLY",
    access_key: str = None,
    secret_key: str = None,
    force_demo: bool = False
):
    """
    Fetches cost and usage data from AWS Cost Explorer, grouped by Region and Service.
    Returns a structured dict with 'regions' (for nested view) and 'consolidated' (service-level total).
    """
    
    # If explicitly forced by frontend, use demo data
    if force_demo:
        return generate_mock_data(start_date, end_date)

    # Resolve credentials passed directly
    has_direct_credentials = access_key is not None and secret_key is not None

    # Determine if we should use demo data from env (ONLY if no credentials provided)
    use_demo_env = os.environ.get('USE_DEMO_DATA', 'false').lower() == 'true'
    
    if not has_direct_credentials and use_demo_env:
        return generate_mock_data(start_date, end_date)

    # Resolve credentials
    final_access_key = access_key or os.environ.get('AWS_ACCESS_KEY_ID')
    final_secret_key = secret_key or os.environ.get('AWS_SECRET_ACCESS_KEY')
    final_region = os.environ.get('AWS_REGION', 'us-east-1')

    if not final_access_key or not final_secret_key:
         if os.environ.get('FALLBACK_TO_DEMO', 'false').lower() == 'true':
             return generate_mock_data(start_date, end_date)
         raise Exception("AWS Credentials not provided and demo mode not active.")

    try:
        client = boto3.client(
            'ce',
            aws_access_key_id=final_access_key,
            aws_secret_access_key=final_secret_key,
            region_name=final_region
        )

        # distinct calls might be needed for perfect strict region grouping vs service grouping,
        # but CostExplorer supports multi-level grouping.
        # GroupBy: Region, Service
        response = client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity=granularity,
            Metrics=['AmortizedCost'],
            GroupBy=[
                {'Type': 'DIMENSION', 'Key': 'REGION'},
                {'Type': 'DIMENSION', 'Key': 'SERVICE'}
            ]
        )
        return format_aws_response_detailed(response)

    except (ClientError, Exception) as e:
        print(f"Error fetching data from AWS: {e}")
        if os.environ.get('FALLBACK_TO_DEMO', 'false').lower() == 'true':
             return generate_mock_data(start_date, end_date)
        raise e

def format_aws_response_detailed(response):
    """
    Formats the boto3 response into a structured JSON for the frontend.
    """
    results_by_time = response.get('ResultsByTime', [])
    
    formatted_data = {
        'total_cost': 0.0,
        'regions': {},       # { "us-east-1": { "total": X, "services": { "EC2": Y } } }
        'consolidated': {},  # { "EC2": { "total": Z, "regions": { "us-east-1": Y } } }
        'period': {'start': '', 'end': ''}
    }

    if not results_by_time:
        return formatted_data
    
    formatted_data['period']['start'] = results_by_time[0]['TimePeriod']['Start']
    formatted_data['period']['end'] = results_by_time[-1]['TimePeriod']['End']

    for result in results_by_time:
        groups = result.get('Groups', [])
        for group in groups:
            # keys are [Region, Service] because of the GroupBy order
            keys = group['Keys']
            region = keys[0]
            service = keys[1] if len(keys) > 1 else "Unknown"
            
            amount = float(group['Metrics']['AmortizedCost']['Amount'])
            
            # --- Region Structure ---
            if region not in formatted_data['regions']:
                formatted_data['regions'][region] = {'total': 0.0, 'services': {}}
            
            formatted_data['regions'][region]['total'] += amount
            if service not in formatted_data['regions'][region]['services']:
                 formatted_data['regions'][region]['services'][service] = 0.0
            formatted_data['regions'][region]['services'][service] += amount

            # --- Consolidated Structure ---
            if service not in formatted_data['consolidated']:
                formatted_data['consolidated'][service] = {'total': 0.0}
            
            formatted_data['consolidated'][service]['total'] += amount
            
            formatted_data['total_cost'] += amount

    # Rounding
    formatted_data['total_cost'] = round(formatted_data['total_cost'], 2)
    
    for r_key, r_val in formatted_data['regions'].items():
        r_val['total'] = round(r_val['total'], 2)
        for s_key, s_val in r_val['services'].items():
            r_val['services'][s_key] = round(s_val, 2)
            
    for c_key, c_val in formatted_data['consolidated'].items():
        c_val['total'] = round(c_val['total'], 2)

    return formatted_data

def generate_mock_data(start_date, end_date):
    """
    Generates realistic looking mock data for demonstration purposes with Service detail.
    """
    regions = ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1', 'sa-east-1']
    services = ['Amazon EC2', 'Amazon RDS', 'Amazon S3', 'AWS Lambda', 'Amazon CloudFront']
    
    data = {
        'total_cost': 0.0,
        'regions': {},
        'consolidated': {},
        'period': {'start': start_date, 'end': end_date}
    }
    
    total = 0
    
    for region in regions:
        region_total = 0
        region_services = {}
        
        # Give some services to each region
        for service in services:
            # Random cost between $10 and $500
            cost = round(random.uniform(10, 500), 2)
            
            region_services[service] = cost
            region_total += cost
            
            # Update consolidated
            if service not in data['consolidated']:
                 data['consolidated'][service] = {'total': 0.0}
            data['consolidated'][service]['total'] += cost
        
        data['regions'][region] = {
            'total': round(region_total, 2),
            'services': region_services
        }
        total += region_total
        
    data['total_cost'] = round(total, 2)
    
    # Round consolidated
    for service in data['consolidated']:
        data['consolidated'][service]['total'] = round(data['consolidated'][service]['total'], 2)
        
    return data
