from django.db import models

class ScopedQuerySet(models.QuerySet):
    def scoped_to(self, auth_context):
        """
        Filters the queryset to match the organization boundary defined in the AuthContext.
        Bypasses filtering if the context represents a global role.
        """
        if auth_context.is_global:
            return self
            
        if not auth_context.org_id:
            return self.none()

        org_field = getattr(self.model, 'org_ownership_field', 'org_id')
        return self.filter(**{org_field: auth_context.org_id})


class ScopedResourceMixin(models.Model):
    """
    Contract for models that are protected by Organization-scoped authorization.
    Requires implementation of `get_owning_org_id` and setting `org_ownership_field`.
    """
    class Meta:
        abstract = True
        
    org_ownership_field = 'org_id' # Used by ScopedQuerySet. Override in subclass if different.

    def get_owning_org_id(self) -> str:
        """
        Returns the UUID of the organization that owns this resource.
        Used by has_object_permission() to enforce mutation boundaries.
        """
        raise NotImplementedError("Protected models must implement get_owning_org_id")
