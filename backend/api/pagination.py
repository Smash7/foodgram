from rest_framework.pagination import LimitOffsetPagination


class LimitSubscriptionsPagination(LimitOffsetPagination):
    default_limit = 15
    page_size_query_param = 'recipes_limit'
