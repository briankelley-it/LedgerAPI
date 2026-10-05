class OwnedQuerysetMixin:
    """Limit a view to records owned by the logged-in user.

    Every model using this has an `owner` foreign key. Because the queryset is
    filtered before DRF looks up a single object, asking for another user's
    record gives a 404, exactly as if it did not exist. A 403 would leak
    the fact that the id is in use.
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        # drf-spectacular builds the schema with an anonymous fake request.
        if getattr(self, "swagger_fake_view", False):
            return queryset.none()
        return queryset.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
