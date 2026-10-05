from rest_framework.routers import DefaultRouter

from apps.ledger.views import BudgetViewSet, CategoryViewSet, ExpenseViewSet

router = DefaultRouter(trailing_slash=True)
# The API root view is not needed: Swagger UI already lists every endpoint.
router.include_root_view = False
router.register("categories", CategoryViewSet, basename="category")
router.register("expenses", ExpenseViewSet, basename="expense")
router.register("budgets", BudgetViewSet, basename="budget")

urlpatterns = router.urls
