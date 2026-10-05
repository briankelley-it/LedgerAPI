from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """Page number pagination where the client may pick a page size up to 100."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
