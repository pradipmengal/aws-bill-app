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
        for service in services:
            cost = round(random.uniform(10, 500), 2)
            region_services[service] = cost
            region_total += cost
            if service not in data['consolidated']:
                 data['consolidated'][service] = {'total': 0.0}
            data['consolidated'][service]['total'] += cost
        data['regions'][region] = {
            'total': round(region_total, 2),
            'services': region_services
        }
        total += region_total
        
    data['total_cost'] = round(total, 2)
    data['daily_cost'] = round(random.uniform(10, 50), 2)
    
    # Round consolidated
    for service in data['consolidated']:
        data['consolidated'][service]['total'] = round(data['consolidated'][service]['total'], 2)
        
    return data

def get_aws_daily_usage(
    access_key: str = None,
    secret_key: str = None,
    force_demo: bool = False
):
    """
    Fetches the cost for the most recent complete day.
    """
    if force_demo:
        return {"daily_cost": round(random.uniform(5, 30), 2)}

    # Resolve credentials
    final_access_key = access_key or os.environ.get('AWS_ACCESS_KEY_ID')
    final_secret_key = secret_key or os.environ.get('AWS_SECRET_ACCESS_KEY')
    final_region = os.environ.get('AWS_REGION', 'us-east-1')

    if not final_access_key or not final_secret_key:
         if os.environ.get('FALLBACK_TO_DEMO', 'false').lower() == 'true':
             return {"daily_cost": round(random.uniform(5, 30), 2)}
         raise Exception("AWS Credentials not provided.")

    try:
        client = boto3.client(
            'ce',
            aws_access_key_id=final_access_key,
            aws_secret_access_key=final_secret_key,
            region_name=final_region
        )

        # Get last 2 days to ensure we have a complete "yesterday"
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        day_before = today - timedelta(days=2)
        
        start = day_before.strftime('%Y-%m-%d')
        end = today.strftime('%Y-%m-%d')

        response = client.get_cost_and_usage(
            TimePeriod={
                'Start': start,
                'End': end
            },
            Granularity='DAILY',
            Metrics=['AmortizedCost']
        )
        
        # Get the latest result
        results = response.get('ResultsByTime', [])
        if results:
            latest = results[-1]
            amount = float(latest.get('Total', {}).get('AmortizedCost', {}).get('Amount', 0.0))
            return {"daily_cost": round(amount, 2)}
        
        return {"daily_cost": 0.0}

    except Exception as e:
        print(f"Error fetching daily cost: {e}")
        if os.environ.get('FALLBACK_TO_DEMO', 'false').lower() == 'true':
             return {"daily_cost": round(random.uniform(5, 30), 2)}
        raise e

def get_daily_cost(
    access_key: str = None,
    secret_key: str = None,
    force_demo: bool = False
):
    """
    Fetches daily cost for the last 7 days from AWS Cost Explorer.
    Returns array of {date, cost} objects.
    """
    if force_demo:
        return generate_mock_daily_cost()

    # Resolve credentials
    final_access_key = access_key or os.environ.get('AWS_ACCESS_KEY_ID')
    final_secret_key = secret_key or os.environ.get('AWS_SECRET_ACCESS_KEY')
    final_region = os.environ.get('AWS_REGION', 'us-east-1')

    if not final_access_key or not final_secret_key:
        if os.environ.get('FALLBACK_TO_DEMO', 'false').lower() == 'true':
            return generate_mock_daily_cost()
        raise Exception("AWS Credentials not provided.")

    try:
        client = boto3.client(
            'ce',
            aws_access_key_id=final_access_key,
            aws_secret_access_key=final_secret_key,
            region_name=final_region
        )

        # Get last 7 days
        today = datetime.now()
        end_date = today
        start_date = today - timedelta(days=7)
        
        start = start_date.strftime('%Y-%m-%d')
        end = end_date.strftime('%Y-%m-%d')

        response = client.get_cost_and_usage(
            TimePeriod={
                'Start': start,
                'End': end
            },
            Granularity='DAILY',
            Metrics=['UnblendedCost']
        )
        
        # Format response
        daily_costs = []
        results = response.get('ResultsByTime', [])
        for result in results:
            date = result['TimePeriod']['Start']
            amount = float(result.get('Total', {}).get('UnblendedCost', {}).get('Amount', 0.0))
            daily_costs.append({
                'date': date,
                'cost': round(amount, 2)
            })
        
        return {'daily_costs': daily_costs}

    except Exception as e:
        print(f"Error fetching daily cost: {e}")
        if os.environ.get('FALLBACK_TO_DEMO', 'false').lower() == 'true':
            return generate_mock_daily_cost()
        raise e

def get_service_cost(
    access_key: str = None,
    secret_key: str = None,
    force_demo: bool = False
):
    """
    Fetches service-wise cost breakdown from AWS Cost Explorer.
    Returns service-wise cost data.
    """
    if force_demo:
        return generate_mock_service_cost()

    # Resolve credentials
    final_access_key = access_key or os.environ.get('AWS_ACCESS_KEY_ID')
    final_secret_key = secret_key or os.environ.get('AWS_SECRET_ACCESS_KEY')
    final_region = os.environ.get('AWS_REGION', 'us-east-1')

    if not final_access_key or not final_secret_key:
        if os.environ.get('FALLBACK_TO_DEMO', 'false').lower() == 'true':
            return generate_mock_service_cost()
        raise Exception("AWS Credentials not provided.")

    try:
        client = boto3.client(
            'ce',
            aws_access_key_id=final_access_key,
            aws_secret_access_key=final_secret_key,
            region_name=final_region
        )

        # Get current month
        today = datetime.now()
        start_date = datetime(today.year, today.month, 1)
        end_date = today
        
        start = start_date.strftime('%Y-%m-%d')
        end = end_date.strftime('%Y-%m-%d')

        response = client.get_cost_and_usage(
            TimePeriod={
                'Start': start,
                'End': end
            },
            Granularity='MONTHLY',
            Metrics=['UnblendedCost'],
            GroupBy=[
                {'Type': 'DIMENSION', 'Key': 'SERVICE'}
            ]
        )
        
        # Format response
        services = {}
        total_cost = 0.0
        
        results = response.get('ResultsByTime', [])
        for result in results:
            for group in result.get('Groups', []):
                service = group['Keys'][0]
                amount = float(group['Metrics']['UnblendedCost']['Amount'])
                
                if service not in services:
                    services[service] = 0.0
                services[service] += amount
                total_cost += amount
        
        # Round values
        for service in services:
            services[service] = round(services[service], 2)
        
        return {
            'services': services,
            'total_cost': round(total_cost, 2)
        }

    except Exception as e:
        print(f"Error fetching service cost: {e}")
        if os.environ.get('FALLBACK_TO_DEMO', 'false').lower() == 'true':
            return generate_mock_service_cost()
        raise e

def get_region_cost(
    access_key: str = None,
    secret_key: str = None,
    force_demo: bool = False
):
    """
    Fetches region-wise cost breakdown from AWS Cost Explorer.
    Returns region-wise cost data.
    """
    if force_demo:
        return generate_mock_region_cost()

    # Resolve credentials
    final_access_key = access_key or os.environ.get('AWS_ACCESS_KEY_ID')
    final_secret_key = secret_key or os.environ.get('AWS_SECRET_ACCESS_KEY')
    final_region = os.environ.get('AWS_REGION', 'us-east-1')

    if not final_access_key or not final_secret_key:
        if os.environ.get('FALLBACK_TO_DEMO', 'false').lower() == 'true':
            return generate_mock_region_cost()
        raise Exception("AWS Credentials not provided.")

    try:
        client = boto3.client(
            'ce',
            aws_access_key_id=final_access_key,
            aws_secret_access_key=final_secret_key,
            region_name=final_region
        )

        # Get current month
        today = datetime.now()
        start_date = datetime(today.year, today.month, 1)
        end_date = today
        
        start = start_date.strftime('%Y-%m-%d')
        end = end_date.strftime('%Y-%m-%d')

        response = client.get_cost_and_usage(
            TimePeriod={
                'Start': start,
                'End': end
            },
            Granularity='MONTHLY',
            Metrics=['UnblendedCost'],
            GroupBy=[
                {'Type': 'DIMENSION', 'Key': 'REGION'}
            ]
        )
        
        # Format response
        regions = {}
        total_cost = 0.0
        
        results = response.get('ResultsByTime', [])
        for result in results:
            for group in result.get('Groups', []):
                region = group['Keys'][0]
                amount = float(group['Metrics']['UnblendedCost']['Amount'])
                
                if region not in regions:
                    regions[region] = 0.0
                regions[region] += amount
                total_cost += amount
        
        # Round values
        for region in regions:
            regions[region] = round(regions[region], 2)
        
        return {
            'regions': regions,
            'total_cost': round(total_cost, 2)
        }

    except Exception as e:
        print(f"Error fetching region cost: {e}")
        if os.environ.get('FALLBACK_TO_DEMO', 'false').lower() == 'true':
            return generate_mock_region_cost()
        raise e

def get_region_service_breakdown(
    access_key: str = None,
    secret_key: str = None,
    force_demo: bool = False
):
    """
    Fetches region-wise cost breakdown with service details from AWS Cost Explorer.
    Returns nested structure: regions -> services -> costs
    """
    if force_demo:
        return generate_mock_region_service_breakdown()

    # Resolve credentials
    final_access_key = access_key or os.environ.get('AWS_ACCESS_KEY_ID')
    final_secret_key = secret_key or os.environ.get('AWS_SECRET_ACCESS_KEY')
    final_region = os.environ.get('AWS_REGION', 'us-east-1')

    if not final_access_key or not final_secret_key:
        if os.environ.get('FALLBACK_TO_DEMO', 'false').lower() == 'true':
            return generate_mock_region_service_breakdown()
        raise Exception("AWS Credentials not provided.")

    try:
        client = boto3.client(
            'ce',
            aws_access_key_id=final_access_key,
            aws_secret_access_key=final_secret_key,
            region_name=final_region
        )

        # Get current month
        today = datetime.now()
        start_date = datetime(today.year, today.month, 1)
        end_date = today
        
        start = start_date.strftime('%Y-%m-%d')
        end = end_date.strftime('%Y-%m-%d')

        response = client.get_cost_and_usage(
            TimePeriod={
                'Start': start,
                'End': end
            },
            Granularity='MONTHLY',
            Metrics=['UnblendedCost'],
            GroupBy=[
                {'Type': 'DIMENSION', 'Key': 'REGION'},
                {'Type': 'DIMENSION', 'Key': 'SERVICE'}
            ]
        )
        
        # Format response
        regions = {}
        total_cost = 0.0
        
        results = response.get('ResultsByTime', [])
        for result in results:
            for group in result.get('Groups', []):
                keys = group['Keys']
                region = keys[0]
                service = keys[1] if len(keys) > 1 else 'Unknown'
                amount = float(group['Metrics']['UnblendedCost']['Amount'])
                
                if region not in regions:
                    regions[region] = {'total': 0.0, 'services': {}}
                
                regions[region]['total'] += amount
                regions[region]['services'][service] = round(amount, 2)
                total_cost += amount
        
        # Round region totals
        for region in regions:
            regions[region]['total'] = round(regions[region]['total'], 2)
        
        return {
            'regions': regions,
            'total_cost': round(total_cost, 2)
        }

    except Exception as e:
        print(f"Error fetching region-service breakdown: {e}")
        if os.environ.get('FALLBACK_TO_DEMO', 'false').lower() == 'true':
            return generate_mock_region_service_breakdown()
        raise e


def get_aws_resource_usage(
    start_date: str, 
    end_date: str, 
    access_key: str = None,
    secret_key: str = None,
    force_demo: bool = False
):
    """
    Fetches resource usage data from AWS Cost Explorer.
    """
    if force_demo:
        return generate_mock_usage_data(start_date, end_date)

    # Resolve credentials
    final_access_key = access_key or os.environ.get('AWS_ACCESS_KEY_ID')
    final_secret_key = secret_key or os.environ.get('AWS_SECRET_ACCESS_KEY')
    final_region = os.environ.get('AWS_REGION', 'us-east-1')

    if not final_access_key or not final_secret_key:
         if os.environ.get('FALLBACK_TO_DEMO', 'false').lower() == 'true':
             return generate_mock_usage_data(start_date, end_date)
         raise Exception("AWS Credentials not provided and demo mode not active.")

    try:
        client = boto3.client(
            'ce',
            aws_access_key_id=final_access_key,
            aws_secret_access_key=final_secret_key,
            region_name=final_region
        )

        response = client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity='MONTHLY',
            Metrics=['UsageQuantity', 'AmortizedCost'],
            GroupBy=[
                {'Type': 'DIMENSION', 'Key': 'SERVICE'},
                {'Type': 'DIMENSION', 'Key': 'USAGE_TYPE'}
            ]
        )
        return format_usage_response(response)

    except (ClientError, Exception) as e:
        print(f"Error fetching usage from AWS: {e}")
        if os.environ.get('FALLBACK_TO_DEMO', 'false').lower() == 'true':
             return generate_mock_usage_data(start_date, end_date)
        raise e

def format_usage_response(response):
    results_by_time = response.get('ResultsByTime', [])
    formatted_data = {
        'regions': {},
        'consolidated': {}, # { "EC2": [ { "type": "t3.medium", "count": 50 } ] }
        'period': {'start': '', 'end': ''}
    }

    if not results_by_time:
        return formatted_data

    formatted_data['period']['start'] = results_by_time[0]['TimePeriod']['Start']
    formatted_data['period']['end'] = results_by_time[-1]['TimePeriod']['End']

    for result in results_by_time:
        for group in result.get('Groups', []):
            keys = group['Keys']
            service = keys[0]
            usage_type = keys[1]
            region = "Global/Linked" # Default since we removed REGION GroupBy
            
            # Clean up usage type
            component = usage_type.split(':')[-1] if ':' in usage_type else usage_type
            
            usage_amount = float(group['Metrics']['UsageQuantity']['Amount'])
            cost_amount = float(group['Metrics']['AmortizedCost']['Amount'])
            
            if usage_amount == 0 and cost_amount == 0: continue

            # --- Region Structure ---
            if region not in formatted_data['regions']:
                formatted_data['regions'][region] = {}
            if service not in formatted_data['regions'][region]:
                formatted_data['regions'][region][service] = []
            
            formatted_data['regions'][region][service].append({
                'component': component,
                'count': round(usage_amount, 2),
                'cost': round(cost_amount, 2),
                'unit': group['Metrics']['UsageQuantity'].get('Unit', '')
            })

            # --- Consolidated Structure ---
            if service not in formatted_data['consolidated']:
                formatted_data['consolidated'][service] = {}
            
            if component not in formatted_data['consolidated'][service]:
                formatted_data['consolidated'][service][component] = {
                    'count': 0.0,
                    'cost': 0.0,
                    'unit': group['Metrics']['UsageQuantity'].get('Unit', '')
                }
            
            formatted_data['consolidated'][service][component]['count'] += usage_amount
            formatted_data['consolidated'][service][component]['cost'] += cost_amount

    # Final touch: convert consolidated dicts to lists for easier JS handling
    final_consolidated = {}
    for svc, components in formatted_data['consolidated'].items():
        final_consolidated[svc] = []
        for comp, data in components.items():
            final_consolidated[svc].append({
                'component': comp,
                'count': round(data['count'], 2),
                'cost': round(data['cost'], 2),
                'unit': data['unit']
            })
    formatted_data['consolidated'] = final_consolidated

    return formatted_data

def generate_mock_usage_data(start_date, end_date):
    regions = ['us-east-1', 'us-west-2', 'eu-west-1']
    services_usage = {
        'Amazon EC2': ['t3.medium', 't3.large', 'm5.xlarge', 'EBS:VolumeUsage (GB)'],
        'Amazon RDS': ['db.t3.small', 'db.m5.large', 'Storage (GB)'],
        'Amazon S3': ['StandardStorage (GB)', 'Requests-Tier1', 'DataTransfer-Out (GB)'],
        'AWS Lambda': ['Invocations', 'Duration (GB-Seconds)']
    }
    
    data = {
        'regions': {},
        'consolidated': {},
        'period': {'start': start_date, 'end': end_date}
    }
    
    for region in regions:
        data['regions'][region] = {}
        for service, components in services_usage.items():
            data['regions'][region][service] = []
            if service not in data['consolidated']:
                data['consolidated'][service] = {}
                
            # Randomly pick some components for this region
            for comp in random.sample(components, random.randint(1, len(components))):
                count = round(random.uniform(1, 1000), 2)
                cost = round(random.uniform(0.1, 50), 2)
                unit = "Units" if "GB" not in comp else "GB"
                
                data['regions'][region][service].append({
                    'component': comp,
                    'count': count,
                    'cost': cost,
                    'unit': unit
                })
                
                if comp not in data['consolidated'][service]:
                    data['consolidated'][service][comp] = {'count': 0, 'cost': 0, 'unit': unit}
                data['consolidated'][service][comp]['count'] += count
                data['consolidated'][service][comp]['cost'] += cost

    # Format consolidated
    final_consolidated = {}
    for svc, components in data['consolidated'].items():
        final_consolidated[svc] = []
        for comp, c_data in components.items():
            final_consolidated[svc].append({
                'component': comp,
                'count': round(c_data['count'], 2),
                'cost': round(c_data['cost'], 2),
                'unit': c_data['unit']
            })
    data['consolidated'] = final_consolidated
            
    return data

def generate_mock_daily_cost():
    """
    Generates mock daily cost data for the last 7 days.
    """
    daily_costs = []
    today = datetime.now()
    
    for i in range(7, 0, -1):
        date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
        cost = round(random.uniform(15, 45), 2)
        daily_costs.append({
            'date': date,
            'cost': cost
        })
    
    return {'daily_costs': daily_costs}

def generate_mock_service_cost():
    """
    Generates mock service-wise cost data.
    """
    services = {
        'Amazon EC2': round(random.uniform(100, 500), 2),
        'Amazon RDS': round(random.uniform(50, 300), 2),
        'Amazon S3': round(random.uniform(20, 150), 2),
        'AWS Lambda': round(random.uniform(10, 100), 2),
        'Amazon CloudFront': round(random.uniform(30, 200), 2),
        'Amazon DynamoDB': round(random.uniform(15, 120), 2),
        'Amazon VPC': round(random.uniform(5, 50), 2)
    }
    
    total_cost = sum(services.values())
    
    return {
        'services': services,
        'total_cost': round(total_cost, 2)
    }

def generate_mock_region_cost():
    """
    Generates mock region-wise cost data.
    """
    regions = {
        'us-east-1': round(random.uniform(200, 600), 2),
        'us-west-2': round(random.uniform(150, 400), 2),
        'eu-west-1': round(random.uniform(100, 350), 2),
        'ap-southeast-1': round(random.uniform(80, 250), 2),
        'ap-northeast-1': round(random.uniform(60, 200), 2),
        'eu-central-1': round(random.uniform(50, 180), 2)
    }
    
    total_cost = sum(regions.values())
    
    return {
        'regions': regions,
        'total_cost': round(total_cost, 2)
    }

def generate_mock_region_service_breakdown():
    """
    Generates mock region-wise cost data with service breakdown.
    """
    services = ['Amazon EC2', 'Amazon RDS', 'Amazon S3', 'AWS Lambda', 'Amazon CloudFront']
    regions_data = {}
    
    regions = ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1', 'ap-northeast-1', 'eu-central-1']
    
    total_cost = 0.0
    for region in regions:
        region_total = 0.0
        region_services = {}
        
        # Each region has 3-5 random services
        num_services = random.randint(3, 5)
        selected_services = random.sample(services, num_services)
        
        for service in selected_services:
            cost = round(random.uniform(10, 150), 2)
            region_services[service] = cost
            region_total += cost
        
        regions_data[region] = {
            'total': round(region_total, 2),
            'services': region_services
        }
        total_cost += region_total
    
    return {
        'regions': regions_data,
        'total_cost': round(total_cost, 2)
    }
