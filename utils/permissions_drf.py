from rest_framework.permissions import BasePermission

def RequireCapability(capability: str):
    """
    DRF Permission Factory that generates a permission class requiring a specific capability.
    
    Usage:
        permission_classes = [RequireCapability('campus:event:manage')]
    """
    class _RequireCapability(BasePermission):
        message = f"You do not have the required capability: {capability}"

        def has_permission(self, request, view):
            auth_context = getattr(request, 'auth_context', None)
            if not auth_context:
                self.message = "Authorization context missing."
                return False
                
            # Global admins bypass capability checks
            if auth_context.is_global:
                return True
                
            if capability not in auth_context.capabilities:
                return False
                
            return True

        def has_object_permission(self, request, view, obj):
            auth_context = getattr(request, 'auth_context', None)
            if not auth_context:
                return False

            if auth_context.is_global:
                return True

            if not hasattr(obj, 'get_owning_org_id'):
                # Failsafe: if the object doesn't implement the contract, deny by default.
                self.message = "Resource does not support organization scoping."
                return False

            owning_org_id = obj.get_owning_org_id()
            if not owning_org_id or owning_org_id != auth_context.org_id:
                self.message = "You do not have permission to access this organization's resource."
                return False

            return True

    return _RequireCapability
