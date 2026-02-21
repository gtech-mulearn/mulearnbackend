def custom_postprocessing_hook(result, generator, **kwargs):
    """
    Automatically groups endpoints by their functional area based on URL structure.
    Example: 
    - /api/v1/dashboard/achievement/... -> "Achievement"
    - /api/v1/dashboard/dynamic-management/... -> "Dynamic Management"
    - /api/v1/register/... -> "Register"
    """
    paths = result.get('paths', {})
    for path, path_obj in paths.items():
        segments = [s for s in path.split('/') if s]
        
        # Default tag
        tag = "General"
        
        if len(segments) >= 3 and segments[0] == 'api' and segments[1] == 'v1':
            if segments[2] == 'dashboard' and len(segments) >= 4:
                # Group by the segment after dashboard: dashboard/achievement -> Achievement
                tag = segments[3].replace('-', ' ').title()
            else:
                # Group by the segment after v1: v1/register -> Register
                tag = segments[2].replace('-', ' ').title()
        
        # Apply the tag to all methods in this path
        for method, operation in path_obj.items():
            if method.lower() in ['get', 'post', 'put', 'patch', 'delete', 'options', 'head']:
                operation['tags'] = [tag]
                
    return result
